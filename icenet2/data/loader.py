import argparse

from icenet2.data.loaders import IceNetDataLoaderFactory
from icenet2.data.cli import add_date_args, process_date_args
from icenet2.utils import setup_logging

"""

"""


@setup_logging
def create_get_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", type=str)
    ap.add_argument("hemisphere", choices=("north", "south"))

    ap.add_argument("-c", "--cfg-only", help="Do not generate data, "
                                             "only config", default=False,
                    action="store_true", dest="cfg")
    ap.add_argument("-d", "--dry",
                    help="Don't output files, just generate data",
                    default=False, action="store_true")
    ap.add_argument("-dt", "--dask-timeouts", type=int, default=120)
    ap.add_argument("-dp", "--dask-port", type=int, default=8888)
    ap.add_argument("-f", "--futures-per-worker", type=float, default=2.,
                    dest="futures")
    ap.add_argument("-fn", "--forecast-name", dest="forecast_name",
                    default=None, type=str)
    ap.add_argument("-fd", "--forecast-days", dest="forecast_days",
                    default=93, type=int)

    ap.add_argument("-l", "--lag", type=int, default=2)

    ap.add_argument("-ob", "--output-batch-size", dest="batch_size", type=int,
                    default=8)

    ap.add_argument("-p", "--pickup", help="Skip existing tfrecords",
                    default=False, action="store_true")
    ap.add_argument("-t", "--tmp-dir", help="Temporary directory",
                    default="/local/tmp", dest="tmp_dir", type=str)

    ap.add_argument("-v", "--verbose", action="store_true", default=False)
    ap.add_argument("-w", "--workers", help="Number of workers to use "
                                            "generating sets",
                    type=int, default=2)

    add_date_args(ap)
    args = ap.parse_args()
    return args


def create():
    # TODO dev #56: collect arguments from staticmethod on implementations
    args = create_get_args()
    dates = process_date_args(args)

    # TODO dev #56: specify implementation from CLI args
    dl = IceNetDataLoaderFactory().create_data_loader(
        "dask",
        "loader.{}.json".format(args.name),
        args.forecast_name if args.forecast_name else args.name,
        args.lag,
        dates_override=dates
        if sum([len(v) for v in dates.values()]) > 0 else None,
        dry=args.dry,
        n_forecast_days=args.forecast_days,
        north=args.hemisphere == "north",
        south=args.hemisphere == "south",
        output_batch_size=args.batch_size,
        pickup=args.pickup,
        generate_workers=args.workers,
        dask_port=args.dask_port,
        futures_per_worker=args.futures)

    if args.cfg:
        dl.write_dataset_config_only()
    else:
        dl.generate()


def get_sample():
    raise NotImplementedError("get_sample is yet to be implemented")
