from abc import abstractmethod

import collections
import glob
import logging
import os

import numpy as np

from icenet2.utils import Hemisphere, HemisphereMixin


class DataProducer(HemisphereMixin):

    @abstractmethod
    def __init__(self, *args,
                 identifier=None,
                 dry=False,
                 overwrite=False,
                 north=True,
                 south=False,
                 path=os.path.join(".", "data"),
                 **kwargs):
        self.dry = dry
        self.overwrite = overwrite

        self._identifier = identifier
        self._path = os.path.join(path, identifier)
        self._hemisphere = (Hemisphere.NORTH if north else Hemisphere.NONE) | \
                           (Hemisphere.SOUTH if south else Hemisphere.NONE)

        if os.path.exists(self._path):
            logging.warning("{} already exists".format(self._path))
        else:
            logging.info("Creating path: {}".format(self._path))
            os.makedirs(self._path, exist_ok=True)

        assert self._identifier, "No identifier supplied"
        assert self._hemisphere != Hemisphere.NONE, "No hemispheres selected"
        # NOTE: specific limitation for the DataProducers, they'll only do one
        # hemisphere per instance
        assert self._hemisphere != Hemisphere.BOTH, "Both hemispheres selected"

    @property
    def base_path(self):
        return self._path

    @base_path.setter
    def base_path(self, path):
        self._path = path

    @property
    def identifier(self):
        return self._identifier

    def get_data_var_folder(self, var, hemisphere=None):
        if not hemisphere:
            # We can make the assumption because this implementation is limited
            # to a single hemisphere
            hemisphere = self.hemisphere_str[0]

        hemi_path = os.path.join(self.base_path, hemisphere)
        if not os.path.exists(hemi_path):
            logging.info("Creating hemisphere path: {}".format(hemi_path))
            os.mkdir(hemi_path)

        var_path = os.path.join(self.base_path, hemisphere, var)
        if not os.path.exists(var_path):
            logging.info("Creating var path: {}".format(var_path))
            os.mkdir(var_path)
        return var_path


class Downloader(DataProducer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abstractmethod
    def download(self):
        raise NotImplementedError("{}.download is abstract".
                                  format(__class__.__name__))


class Generator(DataProducer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abstractmethod
    def generate(self):
        raise NotImplementedError("{}.generate is abstract".
                                  format(__class__.__name__))


class Processor(DataProducer):
    def __init__(self,
                 identifier,
                 source_data,
                 *args,
                 file_filters=tuple(),
                 test_dates=tuple(),
                 train_dates=tuple(),
                 val_dates=tuple(),
                 **kwargs):
        super().__init__(*args,
                         identifier=identifier,
                         **kwargs)

        self._file_filters = list(file_filters)
        self._source_data = os.path.join(source_data, identifier)
        self._var_files = dict()
        self._processed_files = dict()

        # TODO: better as a mixin?
        Dates = collections.namedtuple("Dates", ["train", "val", "test"])
        self._dates = Dates(train=list(train_dates),
                            val=list(val_dates),
                            test=list(test_dates))

    def init_source_data(self):
        path_to_glob = os.path.join(self._source_data,
                                    *self.hemisphere_str)

        if not os.path.exists(path_to_glob):
            raise OSError("Source data directory {} does not exist".
                          format(path_to_glob))

        for date_category in ["train", "val", "test"]:
            dates = getattr(self._dates, date_category)

            if dates:
                logging.info("Processing {} dates for {} category".
                             format(len(dates), date_category))
            else:
                logging.info("No {} dates for this processor".
                             format(date_category))
                continue

            for date in dates:
                globstr = "{}/**/*_{}.nc".format(
                    path_to_glob,
                    date.strftime("%Y%m%d"))

                for df in glob.glob(globstr, recursive=True):
                    if any([flt in os.path.split(df)[1]
                            for flt in self._file_filters]):
                        continue

                    var = os.path.split(df)[0].split(os.sep)[-1]
                    if var not in self._var_files.keys():
                        self._var_files[var] = list()
                    self._var_files[var].append(df)

    @abstractmethod
    def process(self):
        raise NotImplementedError("{}.process is abstract".
                                  format(__class__.__name__))

    def save_processed_file(self, var_name, name, data):
        path = os.path.join(self.get_data_var_folder(var_name), name)
        np.save(path, data)

        if var_name not in self._processed_files.keys():
            self._processed_files[var_name] = list()

        if path not in self._processed_files[var_name]:
            logging.debug("Adding {} file: {}".format(var_name, path))
            self._processed_files[var_name].append(path)
        else:
            logging.warning("{} already exists in {} processed list".
                            format(path, var_name))

    @property
    def dates(self):
        return self._dates

    @property
    def processed_files(self):
        return self._processed_files
