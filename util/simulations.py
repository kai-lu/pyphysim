#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Module docstring"""

__version__ = "$Revision: 5 $"
# $Source$

from collections import OrderedDict, Iterable
import itertools
import copy
import numpy as np

from misc import pretty_time
from util.progressbar import ProgressbarText


# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxx SimulationRunner - START xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
class SimulationRunner():
    """Base class to run simulations.

    You need to derive from this class and implement at least the
    _run_simulation function (see `_run_simulation` help). If a stop
    criterion besides the maximum number of iterations is desired, then you
    need to also reimplement the _keep_going function.

    Note that since _run_simulation receives no argument, then whatever is
    needed must be added to the `params` atribute. That is, in the
    construtor of the derived class call the `add` method of `params` for
    each parameter you need in the _run_simulation function.

    Likewise, the _run_simulation method should return the results as a
    SimulationResults object.
    """
    def __init__(self):
        """
        """
        self.rep_max = 1
        self._elapsed_time = 0.0
        self._runned_reps = []  # Number of iterations performed by
                                # simulation when it finished
        self.params = SimulationParameters()

        self.results = []

        # Message passed to the _get_update_progress_function function. The
        # message can contain "{SomeParameterName}" which will be replaced
        # with the parameter value.
        #
        # If, on the other hand, progressbar_message is None, then the
        # progressbar will be disabled.
        self.progressbar_message = ''

    def _run_simulation(self, current_parameters):
        """Performs the one simulation.

        This function must be implemented in a subclass. It should take the
        needed parameters from the params class attribute (which was filled
        in the constructor of the derived class) and return the results as
        a SimulationResults object.

        Note that _run_simulation will be called self.rep_max times (or
        less if an early stop criteria is reached, which requires
        reimplementing the _keep_going function in the derived class) and
        the results from multiple repetitions will be merged.

        Arguments:

        - `current_parameters`: SimulationParameters object with the
                                parameters for the simulation. The
                                self.params variable is not used
                                directly. It is first unpacked in the
                                simulate function which then calls
                                _run_simulation for each combination.
        """
        NotImplemented("This function must be implemented in a subclass")

    def _keep_going(self, current_sim_results):
        """Check if the simulation should continue or stop.

        This function may be reimplemented in the derived class if a stop
        condition besides the number of iterations is desired.  The idea is
        that _run_simulation returns a SimulationResults object, which is
        then passed to _keep_going, which is then in charge of deciding if
        the simulation should stop or not.

        Arguments:
        - `current_sim_results`: SimulationResults object from the last
                                 iteration (merged with all the previous
                                 results)
        """
        # If this function is not reimplemented in a subclass it always
        # returns True. Therefore, the simulation will only stop when the
        # maximum number of allowed iterations is reached.
        return True

    def _get_update_progress_function(self, message=''):
        """Return a function that should be called to update the
        progressbar.

        The returned function accepts a single argument, corresponding to
        the number of iterations executed so far.

        Arguments:
         - `message`: The message to be written in the progressbar, if
                      it is used.
        """
        # The returned function will update the bar
        self.bar = ProgressbarText(self.rep_max, '*', message)
        return lambda value: self.bar.progress(value)
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    @property
    def elapsed_time(self):
        """property: Get the simulation elapsed time. Do not set this
        value."""
        return pretty_time(self._elapsed_time)

    @property
    def runned_reps(self):
        return self._runned_reps

    def simulate(self):
        """
        """
        # xxxxxxxxxxxxxxx Some initialization xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        from time import time
        tic = time()
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx FOR UNPACKED PARAMETERS xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        for current_params in self.params.get_unpacked_params_list():
            # Get the update_progress_func function
            if self.progressbar_message is None:
                # If self.progressbar_message is None then
                # update_progress_func does nothing
                update_progress_func = lambda value: None
            else:
                update_progress_func = self._get_update_progress_function(
                    self.progressbar_message.format(**current_params.parameters))

            # First iteration
            current_sim_results = self._run_simulation(current_params)
            current_rep = 1

            # Run more iterations until one of the stop criteria is reached
            while (self._keep_going(current_sim_results)
                   and
                   current_rep < self.rep_max):
                current_sim_results.merge_all_results(
                    self._run_simulation(current_params))
                update_progress_func(current_rep + 1)
                current_rep += 1

            # If the while loop ended before rep_max repetitions (because
            # _keep_going returned false) then set the progressbar to full.
            update_progress_func(self.rep_max)

            # Store the number of repetitions actually runned
            self._runned_reps.append(current_rep)
            self.results.append(current_sim_results)
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Update the elapsed time xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        toc = time()
        self._elapsed_time = toc - tic
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxx SimulationRunner - END xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxx SimulationParameters - START xxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
class SimulationParameters():
    """Class to store the simulation parameters.

    A SimulationParameters object acts as a container for all simulation
    parameters. To add a new parameter to the object just call the `add`
    method passing the name and the value of the parameter. The value can
    be anything as long as the _run_simulation function can understand it.
    """
    def __init__(self):
        """
        """
        # Dictionary that will store the parameters. The key is the
        # parameter name and the value is the parameter value.
        self.parameters = {}

        # A set to store the names of the parameters that will be unpacked.
        # Note there is a property to get the parameters marked to be
        # unpacked, that is, the unpacked_parameters property.
        self._unpacked_parameters_set = set()

    @property
    def unpacked_parameters(self):
        # Names of the parameters that will be unpacked.
        return list(self._unpacked_parameters_set)

    @staticmethod
    def create(params_dict):
        """Create a new SimulationParameters object.

        This static method provides a different way to create a
        SimulationParameters object, already containing the parameters in
        the `params_dict` dictionary.

        Arguments:
        - `params_dict`: Dictionary containing the parameters. Each
                         dictionary key corresponds to a parameter.
        """
        sim_params = SimulationParameters()
        sim_params.parameters = copy.deepcopy(params_dict)
        return sim_params

    def add(self, name, value):
        """Add a new parameter.

        If there is already a parameter with the same name it will be
        replaced.

        Arguments:
        - `name`: Name of the parameter
        - `value`: Value of the parameter
        """
        self.parameters[name] = value

    def set_unpack_parameter(self, name, unpack_bool=True):
        """Set the unpack property of the parameter with name `name`

        This is used in the SimulationRunner.
        Arguments:
        - `name`: Name of the parameter to be unpacked
        - `unpack_bool`: True activates unpacking for `name`, False
                         deactivates it
        Raises:
        - ValueError: if `name` is not in parameters or is not iterable.
        """
        if name in self.parameters.keys():
            if isinstance(self.parameters[name], Iterable):
                self._unpacked_parameters_set.add(name)
            else:
                raise ValueError("Parameter {0} is not iterable".format(name))
        else:
            raise ValueError("Unknown parameter: `{0}`".format(name))

    def __getitem__(self, name):
        """Return the parameter with name `name`

        Arguments:
        - `name`: Name of the desired parameter
        """
        return self.parameters[name]

    def __repr__(self):
        def modify_name(name):
            """Add an * in name if it is set to be unpacked"""
            if name in self._unpacked_parameters_set:
                name += '*'
            return name
        repr_list = []
        for name, value in self.parameters.items():
            repr_list.append("'{0}': {1}".format(modify_name(name), value))
        return '{%s}' % ', '.join(repr_list)

    def get_num_parameters(self):
        """Get the number of parameters currently stored.
        """
        return len(self.parameters)

    def get_num_unpacked_variations(self):
        """Get the number of variations when the parameters are unpacked.
        """
        # Generator for the lengths of the parameters set to be unpacked
        gen_values = (len(self.parameters[i]) for i in self._unpacked_parameters_set)
        # Just multiply all the lengths
        return reduce(lambda x, y: x * y, gen_values)

    # Get from
    # https://gist.github.com/1511969/222e3316048bce5763b1004331af898088ffcd9e
    @staticmethod
    def ravel_multi_index(indexes, shape):
        """
        Arguments
        - `indexes`: A list with the indexes
        - `shape`: Shape of the array
        """
        #c order only
        base_c = np.arange(np.prod(shape)).reshape(*shape)
        return base_c[tuple(indexes)]

    # TODO Escrever uma documentação clara e com exemplos de fácil
    # entendimento.
    def get_pack_indexes(self, fixed_params_dict=dict()):
        """When you call the function get_unpacked_params_list you get a
        list of SimulationParameters objects corresponding to all
        combinations of the parameters. The function get_pack_indexes
        allows you to provided all parameters marked to be unpacked but
        one, and returns the indexes of the list returned by
        get_unpacked_params_list that you want.

        Arguments:
        - `fixed_params_dict`: A ditionary with the name of the fixed
                               parameters as keys and the fixed value as
                               value.
        """
        # Get the only parameter that was not fixed
        varying_param = list(
            self._unpacked_parameters_set - set(fixed_params_dict.keys())
            )
        assert len(varying_param) == 1, "All unpacked parameters must be fixed except one"
        # The only parameter still varying. That is, one parameter marked
        # to be unpacked, bu not in fixed_params_dict.
        varying_param = varying_param[0]  # List with one element

        # List to store the indexes (as strings) of the fixed parameters,
        # as well as ":" for the varying parameter,
        param_indexes = []
        for i in self.unpacked_parameters:
            if i == varying_param:
                param_indexes.append(':')
            else:
                fixed_param_value_index = list(self.parameters[i]).index(fixed_params_dict[i])
                param_indexes.append(str(fixed_param_value_index))

        # xxxxx Get the indexes xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        # For this we create a auxiliary numpy array going from 0 to the
        # number of unpack variations. The we use param_indexes to build a
        # string that we can evaluate using the auxiliary numpy array in
        # order to get the linear indexes.

        # Get the lengths of the parameters marked to be unpacked
        dimensions = [len(self.parameters[i]) for i in self.unpacked_parameters]
        aux = np.arange(0, self.get_num_unpacked_variations())
        aux.shape = dimensions
        indexes = eval("aux" + "[{0}]".format(",".join(param_indexes)))
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        return indexes

    def get_unpacked_params_list(self):
        """Get a list of SimulationParameters objects, each one
        corresponding to a possible combination of (unpacked) parameters.

        Supose you have a SimulationParameters object with the parameters
        a=1, b=2, c=[3,4] and d=[5,6]
        and the parameters `c` and `d` were set to be unpacked.  Then
        get_unpacked_params_list would return a list of four
        SimulationParameters objects with parameters (the order
        may be different)
        {'a': 1, 'c': 3, 'b': 2, 'd': 5}
        {'a': 1, 'c': 3, 'b': 2, 'd': 6}
        {'a': 1, 'c': 4, 'b': 2, 'd': 5}
        {'a': 1, 'c': 4, 'b': 2, 'd': 6}
        """
        # If unpacked_parameters is empty, return self
        if not self._unpacked_parameters_set:
            return [self]

        # Lambda function to get an iterator to a (iterable) parameter
        # given its name
        get_iter_from_name = lambda name: iter(self.parameters[name])

        # Dictionary that stores the name and an iterator of a parameter
        # marked to be unpacked
        unpacked_params_iter_dict = OrderedDict()
        for i in self._unpacked_parameters_set:
            unpacked_params_iter_dict[i] = get_iter_from_name(i)
        keys = unpacked_params_iter_dict.keys()

        # Using itertools.product we can convert the multiple iterators
        # (for the different parameters marked to be unpacked) to a single
        # iterator that returns all the possible combinations (cartesian
        # product) of the individual iterators.
        all_combinations = itertools.product(*(unpacked_params_iter_dict.values()))

        # Names of the parameters that don't need to be unpacked
        regular_params = set(self.parameters.keys()) - self._unpacked_parameters_set

        # Constructs a list with dictionaries, where each dictionary
        # corresponds to a possible parameters combination
        unpack_params_length = len(self._unpacked_parameters_set)
        all_possible_dicts_list = []
        for comb in all_combinations:
            new_dict = {}
            # Add current combination of the unpacked parameters
            for index in range(unpack_params_length):
                new_dict[keys[index]] = comb[index]
            # Add the regular parameters
            for param in regular_params:
                new_dict[param] = self.parameters[param]
            all_possible_dicts_list.append(new_dict)

        # Map the list of dictionaries to a list of SimulationParameters
        # objects and return it
        return map(SimulationParameters.create, all_possible_dicts_list)

    def save_to_file(self, file_name):
        """Save the SimulationParameters object to the file `file_name`.

        Arguments:
        - `file_name`: Name of the file to save the parameters.
        """
        NotImplemented("SimulationParameters.save_to_file: Implement-me")
# xxxxxxxxxx SimulationParameters - END xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxx SimulationResults - START xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
class SimulationResults():
    """Store results from simulations.

    This class is used in the SimulationRunner class in order to store
    results from each simulation. It is able to combine the results from
    multiple simulations.

    >>> result1 = Result("lala", Result.SUMTYPE)
    >>> result1.update(13)
    >>> result2 = Result("lele", Result.RATIOTYPE)
    >>> result2.update(3, 10)
    >>> result2.update(8, 10)
    >>> simresults = SimulationResults()
    >>> simresults.add_result(result1)
    >>> simresults.add_result(result2)
    >>> simresults.get_result_names()
    ['lele', 'lala']
    >>> simresults
    SimulationResults: ['lele', 'lala']

    >>> result1_other = Result('lala', Result.SUMTYPE)
    >>> result1_other.update(7)
    >>> simresults.append_result(result1_other)
    >>> simresults.get_result_values_list('lala')
    [13, 7]
    >>> simresults['lala']
    [Result -> lala: 13, Result -> lala: 7]
    >>> len(simresults)
    2

    >>> result3 = Result("lala", Result.SUMTYPE)
    >>> result3.update(2)
    >>> result4 = Result("lele", Result.RATIOTYPE)
    >>> result4.update(1, 2)
    >>> result4.update(3, 3)
    >>> simresults2 = SimulationResults()
    >>> simresults2.add_result(result3)
    >>> simresults2.add_result(result4)
    >>> simresults2.merge_all_results(simresults)
    >>> simresults2['lala']
    [Result -> lala: 9]
    >>> simresults2['lele']
    [Result -> lele: 15/25 -> 0.6]
    >>> simresults3 = SimulationResults()
    >>> simresults3.append_all_results(simresults)
    >>> simresults3['lala']
    [Result -> lala: 13, Result -> lala: 7]
    >>> simresults3['lele']
    [Result -> lele: 11/20 -> 0.55]
    """
    def __init__(self):
        self._results = dict()

    def __repr__(self):
        lista = [i for i in self._results.keys()]
        repr = "SimulationResults: %s" % lista
        return repr

    def add_result(self, result):
        """Add a new result to the SimulationResults object. If there is
        already a result stored with the same name, this will replace it.

        Arguments:
        - `result`: Must be an object of the Result class.
        """
        # Added as a list with a single element
        self._results[result.name] = [result]

    def append_result(self, result):
        """Append a result to the SimulationResults object. This
        efectivelly means that the SimulationResults object will now store
        a list for the given result name. This allow you, for instance, to
        store multiple bit error rates with the 'BER' name such that
        simulation_results_object['BER'] will return a list with the Result
        objects for each value.

        Note that if multiple values for some Result are stored, then only
        the last value can be updated with merge_all_results.

        Arguments:
        - `result`: A Result object

        """
        if result.name in self._results.keys():
            self._results[result.name].append(result)
        else:
            self.add_result(result)

    def append_all_results(self, other):
        """Append all the results of the other SimulationResults object
        with self.

        Arguments:
        - `other`: Another SimulationResults object

        """
        for results in other:
            # There can be more then one value for the same result name
            for result in results:
                self.append_result(result)

    def merge_all_results(self, other):
        """Merge all the results of the other SimulationResults object with
        the results in self.

        When there is more then one result with the same name stored in
        self (for instance two bit error rates) then only the last one will
        be merged with the one in "other". That also means that only one
        result for that name should be stored in "other".

        Arguments:
        - `other`: Another SimulationResults object

        """
        # If the current SimulationResults object is empty, we basically
        # copy the Result objects from other
        if len(self) == 0:
            for name in other.get_result_names():
                self._results[name] = other[name]
        # Otherwise, we merge each Result from `self` with the Result from
        # `other`
        else:
            for item in self._results.keys():
                self._results[item][-1].merge(other[item][-1])

    def get_result_names(self):
        return self._results.keys()

    def get_result_values_list(self, result_name):
        """Get the values for the results with name "result_name"

        Returns a list with the values.

        Arguments:
        - `result_name`: A string
        """
        return [i.value for i in self[result_name]]

    def __getitem__(self, key):
        # if key in self._results.keys():
        return self._results[key]
        # else:
        #     raise KeyError("Invalid key: %s" % key)

    def __len__(self):
        """Get the number of results stored in self.
        """
        return len(self._results)

    def __iter__(self):
        # """Get an iterator to the internal dictionary. Therefore iterating
        # through this will iterate through the dictionary keys, that is, the
        # name of the results stored in the SimulationResults object.
        # """
        """Get an iterator to the results stored in the SimulationResults
        object.
        """
        return self._results.itervalues()
# xxxxxxxxxx SimulationResults - END xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxx Result - START xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
class Result():
    """Class to store a single simulation result.

    The simulation result can be anything, such as the number of errors, a
    string, an error rate, etc. When creating a Result object one needs to
    specify only the name of the stored result and the result type.

    The diferent types indicate how the Result can be updated (combined
    with other samples). The possible values are SUMTYPE, RATIOTYPE and
    STRINGTYPE.

    In the SUMTYPE the new value should be added to current one in update
    function.

    In the RATIOTYPE the new value should be added to current one and total
    should be also updated in the update function. One caveat is that rates
    are stored as a number (numerator) and a total (denominator) instead of
    as a float.

    In the STRINGTYPE the update should replace current the value, since it
    is a string.

    >>> result1 = Result("name", Result.SUMTYPE)
    >>> result1.update(13)
    >>> result1.update(4)
    >>> result1.value
    17
    >>> result1.get_result()
    17
    >>> result1.num_updates
    2
    >>> result1
    Result -> name: 17
    >>> result1.get_type_name()
    'SUMTYPE'
    >>> result1.get_type()
    0
    >>> print result1
    Result -> name: 17

    >>> result2 = Result("name2", Result.RATIOTYPE)
    >>> result2.update(4,10)
    >>> result2.update(3,4)
    >>> result2.get_result()
    0.5
    >>> result2.get_type_name()
    'RATIOTYPE'
    >>> result2.get_type()
    1
    >>> result2_other = Result("name2", Result.RATIOTYPE)
    >>> result2_other.update(3,11)
    >>> result2_other.merge(result2)
    >>> result2_other.get_result()
    0.4
    >>> result2_other.num_updates
    3
    >>> result2_other.value
    10
    >>> result2_other.total
    25
    >>> print result2_other
    Result -> name2: 10/25 -> 0.4
    """
    # Like an Enumeration for the type of results.
    (SUMTYPE, RATIOTYPE, STRINGTYPE, FLOATTYPE) = range(4)
    all_types = {
        SUMTYPE: "SUMTYPE",
        RATIOTYPE: "RATIOTYPE",
        STRINGTYPE: "STRINGTYPE",
        FLOATTYPE: "FLOATTYPE",
    }

    def __init__(self, name, update_type):
        """
        """
        self.name = name
        self.__update_type = update_type
        self.value = 0
        self.total = 0
        self.num_updates = 0  # Number of times the Result object was
                              # updated

    @staticmethod
    def create(name, update_type, value, total=0):
        """Create a Result object and update it with `value` and `total` at
        the same time.

        Equivalent to creating the object and then call its update
        function.

        Arguments:
        - `name`:
        - `update_type`:
        - `value`:
        - `total`:
        """
        result = Result(name, update_type)
        result.update(value, total)
        return result

    def __repr__(self):
        if self.__update_type == Result.RATIOTYPE:
            v = self.value
            t = self.total
            return "Result -> {0}: {1}/{2} -> {3}".format(
                self.name, v, t, float(v) / t)
        else:
            return "Result -> {0}: {1}".format(self.name, self.get_result())

    def update(self, value, total=0):
        """Update the current value.

        Arguments:
        - `value`: Value to be added to (or replaced) the current value
        - `total`: Value to be added to (if applied) the current total
          (only useful for the RATIOTYPE update type)

        How the update is performed for each Result type
        - RATIOTYPE: Add "value" to current value and "total" to current total
        - SUMTYPE: Add "value" to current value. "total" is ignored.
        - STRINGTYPE: Replace the current value with "value".
        - FLOATTYPE: Replace the current value with "value".

        """
        self.num_updates += 1

        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        # Python does not have a switch statement. We use dictionaries as
        # the equivalent of a switch statement.
        # First we define a function for each possibility.
        def __default_update(ignored1, ignored2):
            print("Warning: update not performed for unknown type %s" %
                  self.__update_type)
            pass

        def __update_SUMTYPE_value(value, ignored):
            self.value += value

        def __update_RATIOTYPE_value(value, total):
            assert value <= total, ("__update_RATIOTYPE_value: "
                                    "'value cannot be greater then total'")
            if total == 0:
                print("Update Ignored: total should be provided and be greater "
                      "then 0 when the update type is RATIOTYPE")
            else:
                self.value += value
                self.total += total

        def __update_by_replacing_current_value(value, ignored):
            self.value = value
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # Now we fill the dictionary with the functions
        possible_updates = {
            Result.RATIOTYPE: __update_RATIOTYPE_value,
            Result.STRINGTYPE: __update_by_replacing_current_value,
            Result.SUMTYPE: __update_SUMTYPE_value,
            Result.FLOATTYPE: __update_by_replacing_current_value
            }

        # Call the apropriated update method. If self.__update_type does
        # not contain a key in the possible_updates dictionary (that is, a
        # valid update type), then the function __default_update is called.
        possible_updates.get(self.__update_type,
                             __default_update)(value, total)

    def get_type_name(self):
        return Result.all_types[self.__update_type]

    def get_type(self):
        """Get the Result type.

        The returned value is one of the keys in Result.all_types.
        """
        return self.__update_type

    def merge(self, other):
        """Merge the result from other with self.

        Arguments:
        - `other`: Another Result object.
        """
        assert self.__update_type == other.__update_type, (
            "Can only merge to objects with the same name and type")
        assert self.__update_type != Result.STRINGTYPE, (
            "Cannot merge results of the STRINGTYPE type")
        assert self.name == other.name, (
            "Can only merge to objects with the same name and update_type")
        self.num_updates += other.num_updates
        self.value += other.value
        self.total += other.total

    def get_result(self):
        if self.num_updates == 0:
            return "Nothing yet".format(self.name)
        else:
            if self.__update_type == Result.RATIOTYPE:
                #assert self.total != 0, 'Total should not be zero'
                return float(self.value) / self.total
            else:
                return self.value
# xxxxxxxxxx Result - END xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


# xxxxx Perform the doctests xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
if __name__ == '__main__':
    # import os
    # import sys
    # from exceptions import NameError

    # # Add the parent folder to the path.
    # try:
    #     # If this file is executed the __file__ will be defined and we add
    #     # the parent folder to the path, considering the file location
    #     cmd_folder = os.path.dirname(os.path.abspath(__file__))
    # except NameError, e:
    #     # If the content of this file is executed as a script then __file__
    #     # will not be defined and we add the parent folder of the current
    #     # working directory to the path
    #         cmd_folder = os.getcwd()
    # finally:
    #     if cmd_folder not in sys.path:
    #         # Add the parent folder to the beggining of the path
    #         sys.path.insert(0, cmd_folder)

    # When this module is run as a script the doctests are executed
    import doctest
    doctest.testmod()
    print "simulations.py executed"
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx