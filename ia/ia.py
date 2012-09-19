#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""Module with implementation of Interference Alignment algorithms"""

import numpy as np

from misc import peig, leig, randn_c


# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxx MultiUserChannelMatrix Class xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
class MultiUserChannelMatrix(object):
    """Stores the (fast fading) channel matrix of a multi-user scenario.

    This channel matrix can be seem as an concatenation of blocks (of
    non-uniform size) where each block is a channel from one transmitter to
    one receiver and the block size is equal to the number of receive
    antennas of the receiver times the number of transmit antennas of the
    transmitter.

    For instance, in a 3-users scenario the block (1,0) corresponds to the
    channel between the transmit antennas of user 0 and the receive
    antennas of user 1 (indexing staring at zero). If the number of receive
    antennas and transmit antennas of the three users are [2, 4, 6] and
    [2, 3, 5], respectively, then the block (1,0) would have a dimension of
    4x2. Likewise, the channel matrix would look similar to the block
    structure below.
                +------+---------+---------------+
                |2 x 2 |  2 x 3  |     2 x 5     |
                |      |         |               |
                +------+---------+---------------+
                |4 x 2 |  4 x 3  |     4 x 5     |
                |      |         |               |
                |      |         |               |
                |      |         |               |
                +------+---------+---------------+
                |6 x 2 |  6 x 3  |     6 x 5     |
                |      |         |               |
                |      |         |               |
                |      |         |               |
                |      |         |               |
                |      |         |               |
                +------+---------+---------------+

    It is possible to initialize the channel matrix randomly by calling the
    `randomize` method, or from a given matrix by calling the
    `init_from_channel_matrix` method.

    In order to get the channel matrix of a specific user `k` to another
    user `l`, call the `getChannel` method.
    """

    def __init__(self, ):
        self.H = np.array([])
        self.Nr = np.array([])
        self.Nt = np.array([])
        self.K = 0

    def init_from_channel_matrix(self, channel_matrix, Nr, Nt, K):
        """Initializes the multiuser channel matrix from the given
        `channel_matrix`.

        Arguments:
        - `channel_matrix`: A matrix concatenating the channel of all users
                            (from each transmitter to each receiver).
        - `Nr`: An array with the number of receive antennas of each user.
        - `Nt`: An array with the number of transmit antennas of each user.
        - `K`: (int) Number of users.

        Raises: ValueError if the arguments are invalid.
        """
        if channel_matrix.shape != (np.sum(Nr), np.sum(Nt)):
            raise ValueError("Shape of the channel_matrix must be equal to the sum or receive antennas of all users times the sum of the receive antennas of all users.")

        if Nr.size != Nt.size:
            raise ValueError("K must be equal to the number of elements in Nr and Nt")
        if Nt.size != K:
            raise ValueError("K must be equal to the number of elements in Nr and Nt")

        self.K = K
        self.Nr = Nr
        self.Nt = Nt
        self.H = channel_matrix

    def randomize(self, Nr, Nt, K):
        """Generates a random channel matrix for all users.

        Arguments:
        - `K`: (int) Number of users.
        - `Nr`: (array or int) Number of receive antennas of each user. If
                an integer is specified, all users will have that number of
                receive antennas.
        - `Nt`: (array or int) Number of transmit antennas of each user. If
                an integer is specified, all users will have that number of
                receive antennas.
        """
        if isinstance(Nr, int):
            Nr = np.ones(K) * Nr
        if isinstance(Nt, int):
            Nt = np.ones(K) * Nt

        self.Nr = Nr
        self.Nt = Nt
        self.K = K
        self.H = randn_c(np.sum(Nr), np.sum(Nt))

    def getChannel(self, k, l):
        """Get the channel from user l to user k.

        Arguments:
        - `l`: Transmitting user.
        - `k`: Receiving user
        """
        cumNr = np.hstack([0, np.cumsum(self.Nr)])
        cumNt = np.hstack([0, np.cumsum(self.Nt)])

        return self.H[cumNr[k]:cumNr[k + 1], cumNt[l]:cumNt[l + 1]]


# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxx AlternatingMinIASolver Class xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
class AlternatingMinIASolver(object):
    """Implements the "Interference Alignment via % Alternating
    Minimization" algorithm from the paper with the same name.

    Read only variables:
    - K
    - Nt
    - Nr
    - Ns
    """
    def __init__(self, ):
        """
        """
        # The F and W variables will be numpy arrays OF numpy arrays.
        self.F = np.array([])  # Precoder: One precoder for each user
        self.W = np.array([])  # Receive filter: One for each user
        self._multiUserChannel = MultiUserChannelMatrix()  # Channel of all users
        self.C = []    # Basis of the interference subspace for each user

        # xxxxxxxxxx Private attributes xxxxxxxxxxxxxxx
        self._Ns = 0    # Number of streams per user

    # xxxxx Properties to read the channel related variables xxxxxxxxxxxxxx
    @property
    def K(self):
        """The number of users.
        """
        return self._multiUserChannel.K

    @property
    def Nr(self):
        """Number of receive antennas of all users.
        """
        return self._multiUserChannel.Nr

    @property
    def Nt(self):
        """Number of transmit antennas of all users.
        """
        return self._multiUserChannel.Nt

    @property
    def Ns(self):
        """Number of streams of all users.
        """
        return self._Ns

    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    def getCost(self):
        """Get the Cost of the algorithm for the current iteration of the
        precoder.
        """
        Cost = 0
        for k in np.arange(self.K):
            for l in np.arange(self.K):
                if l != k:
                    Hkl_Fl = np.dot(
                        self.getChannel(k, l),
                        self.F[l])
                    Cost = Cost + np.linalg.norm(
                        Hkl_Fl -
                        np.dot(
                            np.dot(
                                self.C[k],
                                self.C[k].transpose().conjugate()),
                            Hkl_Fl
                        ), 'fro') ** 2
        return Cost

    def step(self):
        """Step the algorithm
        """
        self.updateC()
        self.updateF()
        self.updateW()

    # TODO: Try to reimplement in a more efficient way without for loops
    def updateC(self):
        """Update the value of Ck for all K users.

        Ck contains the orthogonal basis of the interference subspace of
        user k. It corresponds to the Nk-Sk dominant eigenvectors of
        $\sum_{l \neq k} H_{k,l} F_l F_l^H H_{k,l}^H$
        """
        self.C = np.zeros(self.K, dtype=np.ndarray)
        for k in np.arange(self.K):
            self.C[k] = np.zeros(self.Nr[k])
            for l in np.arange(self.K):
                if k != l:
                    Hkl_F = np.dot(
                        self.getChannel(k, l),
                        self.F[l]
                        )
                    self.C[k] = self.C[k] + np.dot(Hkl_F, Hkl_F.transpose().conjugate())
            # TODO: implement and test with external interference
            # # We are inside only of the first for loop
            # # Add the external interference contribution
            # self.C[k] = obj.C{k} + obj.Rk{k}

            Ni = self.Nr[k] - self.Ns[k]
            # C[k] will receive the Ni most dominant eigenvectors of C[k]
            self.C[k] = peig(self.C[k], Ni)[0]

    def updateF(self):
        """Update the value of the precoder of all K users.

        Fl, the precoder of the l-th user, tries avoid as much as possible
        to send energy into the desired signal subspace of the other
        users. Fl contains the Sl least dominant eigenvectors of
        $\sum_{k \neq l} H_{k,l}^H (I - C_k C_k^H)H_{k,l}$
        """
        # xxxxx Calculates the temporary variable Y[k] for all k xxxxxxxxxx
        # Note that $Y[k] = (I - C_k C_k^H)$
        Y = np.zeros(self.K, dtype=np.ndarray)

        # TODO: Perform benchmarks and try to replace this maybe with a
        # ufunc to avoid the for loop
        for k in np.arange(self.K):
            Y[k] = np.eye(self.Nr[k], dtype=complex) - \
                   np.dot(
                       self.C[k],
                       self.C[k].conjugate().transpose())

        # g = np.vectorize(lambda Ck, Nrk: np.eye(Nrk, dtype=complex) - \
        #                  np.dot(
        #                      self.Ck,
        #                      self.Ck.conjugate().transpose()))
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        newF = np.zeros(self.K, dtype=np.ndarray)
        for l in np.arange(self.K):
            newF[l] = np.zeros(self.Nt[l], self.Nt[l])
            for k in np.arange(self.K):
                if k != l:
                    lH = self.getChannel(k, l)
                    newF[l] = newF[l] + np.dot(
                        np.dot(lH.conjugate().transpose(),
                               Y[k]),
                        lH)

            newF[l] = leig(newF[l], self.Ns[l])[0]
        self.F = newF

    def updateW(self):
        """Update the zero-forcing filters.

        The zero-forcing filter is calculated in the paper "MIMO
        Interference Alignment Over Correlated Channels with Imperfect
        CSI".
        """
        newW = np.zeros(self.K, dtype=np.ndarray)
        for k in np.arange(self.K):
            tildeHi = np.hstack(
                [np.dot(self.getChannel(k, k), self.F[k]),
                 self.C[k]])
            newW[k] = np.linalg.inv(tildeHi)
            # We only want the first Ns[k] lines
            newW[k] = newW[k][0:self.Ns[k]]
        self.W = newW

    def randomizeF(self, Nt, Ns, K):
        """Generates a random precoder for each user.

        Arguments:
        - `K`: Number of users.
        - `Nt`: Number of transmit antennas of each user
        - `Ns`: Number of streams of each user.
        """
        if isinstance(Ns, int):
            Ns = np.ones(K) * Ns
        if isinstance(Nt, int):
            Nt = np.ones(K) * Nt

        # Lambda function that returns a normalized version of the input
        # numpy array
        normalized = lambda A: A / np.linalg.norm(A, 'fro')

        self.F = np.zeros(K, dtype=np.ndarray)
        for k in range(K):
            self.F[k] = normalized(randn_c(Nt[k], Ns[k]))
        #self.F = [normalized(randn_c(Nt[k], Ns[k])) for k in np.arange(0, K)]
        self._Ns = Ns

    def randomizeH(self, Nr, Nt, K):
        """Generates a random channel matrix for all users.

        Arguments:
        - `K`: (int) Number of users.
        - `Nr`: (array or int) Number of receive antennas of each user
        - `Nt`: (array or int) Number of transmit antennas of each user
        """
        self._multiUserChannel.randomize(Nr, Nt, K)

    # This method does not need testing, since the logic is implemented in
    # the MultiUserChannelMatrix class and it is already tested.
    def init_from_channel_matrix(self, channel_matrix, Nr, Nt, K):
        """Initializes the multiuser channel matrix from the given
        `channel_matrix`.

        Arguments:
        - `channel_matrix`: A matrix concatenating the channel of all users
                            (from each transmitter to each receiver).
        - `Nr`: An array with the number of receive antennas of each user.
        - `Nt`: An array with the number of transmit antennas of each user.
        - `K`: (int) Number of users.

        Raises: ValueError if the arguments are invalid.
        """
        self._multiUserChannel.init_from_channel_matrix(channel_matrix, Nr,
                                                       Nt, K)

    # This method does not need testing, since the logic is implemented in
    # the MultiUserChannelMatrix class and it is already tested.
    def getChannel(self, k, l):
        """Get the channel from user l to user k.

        Arguments:
        - `l`: Transmitting user.
        - `k`: Receiving user
        """
        return self._multiUserChannel.getChannel(k, l)


# xxxxx Perform the doctests xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
if __name__ == '__main__':
    # When this module is run as a script the doctests are executed
    import doctest
    doctest.testmod()
    print "{0} executed".format(__file__)
