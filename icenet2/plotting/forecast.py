import argparse
import logging
import os

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation

import numpy as np
import pandas as pd

from icenet2.data.cli import date_arg
from icenet2.data.sic.mask import Masks
from icenet2.plotting.utils import \
    get_forecast_obs_da, get_forecast_hres_obs_da

matplotlib.rcParams.update({
    'figure.facecolor': 'w',
    'figure.dpi': 300
})


def plot_binary_accuracy(masks: object,
                         fc_da: object,
                         cmp_da: object,
                         obs_da: object,
                         output_path: object =
                         os.path.join("plot", "binacc.png")) -> object:
    """
    TODO: Split out getting and plotting binary accuracy
    :param masks:
    :param fc_da:
    :param cmp_da:
    :param obs_da:
    :param output_path:
    :return:
    """
    agcm = masks.get_active_cell_da(obs_da)
    binary_obs_da = obs_da > 0.15

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_title("Binary accuracy comparison")

    binary_fc_da = fc_da > 0.15
    binary_fc_da = (binary_fc_da == binary_obs_da).\
        astype(np.float16).weighted(agcm)
    binacc_fc = (binary_fc_da.mean(dim=['yc', 'xc']) * 100)
    ax.plot(binacc_fc.time, binacc_fc.values, label="IceNet")

    if cmp_da is not None:
        binary_cmp_da = cmp_da > 0.15
        binary_cmp_da = (binary_cmp_da == binary_obs_da).\
            astype(np.float16).weighted(agcm)
        binacc_cmp = (binary_cmp_da.mean(dim=['yc', 'xc']) * 100)
        ax.plot(binacc_cmp.time, binacc_cmp.values, label="HRES")
    else:
        binacc_cmp = None

    ax.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_minor_locator(mdates.DayLocator())
    ax.legend(loc='lower right')
    plt.savefig(output_path)

    return binacc_fc, binacc_cmp


def sic_error_video(fc_da: object,
                    obs_da: object,
                    land_mask: object,
                    output_path: object =
                    os.path.join("plot", "sic_error.mp4")) -> object:
    """

    :param fc_da:
    :param obs_da:
    :param land_mask:
    :param output_path:
    """

    diff = fc_da - obs_da

    fig, maps = plt.subplots(nrows=1, ncols=3, figsize=(18, 5))
    fig.set_dpi(150)

    leadtime = 0
    fc_plot = fc_da.isel(time=leadtime).to_numpy()
    obs_plot = obs_da.isel(time=leadtime).to_numpy()
    diff_plot = diff.isel(time=leadtime).to_numpy()

    contour_kwargs = dict(
        vmin=0,
        vmax=1,
        cmap='YlOrRd'
    )

    im1 = maps[0].imshow(fc_plot, **contour_kwargs)
    im2 = maps[1].imshow(obs_plot, **contour_kwargs)
    im3 = maps[2].imshow(diff_plot, 
                         vmin=-1, vmax=1, cmap="RdBu_r")

    tic = maps[0].set_title("IceNet {}".format(
        pd.to_datetime(fc_da.isel(time=leadtime).time.values).strftime("%d/%m/%Y")))
    tio = maps[1].set_title("OSISAF Obs {}".format(
        pd.to_datetime(obs_da.isel(time=leadtime).time.values).strftime("%d/%m/%Y")))
    maps[2].set_title("Diff")

    p0 = maps[0].get_position().get_points().flatten()
    p1 = maps[1].get_position().get_points().flatten()
    p2 = maps[2].get_position().get_points().flatten()

    ax_cbar = fig.add_axes([p0[0], 0, p1[2]-p0[0], 0.05])
    plt.colorbar(im1, cax=ax_cbar, orientation='horizontal')

    ax_cbar1 = fig.add_axes([p2[0], 0, p2[2]-p2[0], 0.05])
    plt.colorbar(im3, cax=ax_cbar1, orientation='horizontal')

    for m_ax in maps[0:3]:
        m_ax.contourf(land_mask,
                      levels=[.5, 1],
                      colors=[matplotlib.cm.gray(180)],
                      zorder=3)

    fig.subplots_adjust(hspace=0.2, wspace=0.2)

    def update(date):
        logging.debug("Plotting {}".format(date))

        fc_plot = fc_da.isel(time=date).to_numpy()
        obs_plot = obs_da.isel(time=date).to_numpy()
        diff_plot = diff.isel(time=date).to_numpy()
        
        tic.set_text("IceNet {}".format(
            pd.to_datetime(fc_da.isel(time=date).time.values).strftime("%d/%m/%Y")))
        tio.set_text("OSISAF Obs {}".format(
            pd.to_datetime(obs_da.isel(time=date).time.values).strftime("%d/%m/%Y")))

        im1.set_data(fc_plot)
        im2.set_data(obs_plot)
        im3.set_data(diff_plot)

        return tic, tio, im1, im2, im3

    animation = FuncAnimation(fig,
                              update,
                              range(0, len(fc_da.time)),
                              interval=100)

    plt.close()

    logging.info("Saving plot to {}".format(output_path))
    animation.save(output_path,
                   fps=10,
                   extra_args=['-vcodec', 'libx264'])
    return animation


def forecast_plot_args() -> object:
    """

    :return:
    """

    ap = argparse.ArgumentParser()
    ap.add_argument("hemisphere", choices=("north", "south"))
    ap.add_argument("forecast_file", type=str)
    ap.add_argument("forecast_date", type=date_arg)

    ap.add_argument("-o", "--output-path", type=str, default=None)
    ap.add_argument("-v", "--verbose", action="store_true", default=False)
    ap.add_argument("-e", "--ecmwf", action="store_true", default=False)

    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    return args


def binary_accuracy():
    args = forecast_plot_args()
    kwargs = {}

    if args.output_path:
        kwargs["output_path"] = args.output_path

    fc, obs, _ = get_forecast_obs_da(args.hemisphere,
                                     args.forecast_file,
                                     args.forecast_date)

    hres = None

    if args.ecmwf:
        hres, _, _ = get_forecast_hres_obs_da(args.hemisphere,
                                              obs.time.values[0],
                                              obs.time.values[-1])

    # TODO: split down the get_*_da methods
    masks = Masks(north=args.hemisphere == "north",
                  south=args.hemisphere == "south")
    plot_binary_accuracy(masks,
                         fc,
                         hres,
                         obs,
                         **kwargs)


def sic_error():
    """
    TODO: Allow single frame rendering
    """
    args = forecast_plot_args()
    kwargs = {}

    if args.output_path:
        kwargs["output_path"] = args.output_path

    sic_error_video(*get_forecast_obs_da(args.hemisphere,
                                         args.forecast_file,
                                         args.forecast_date),
                    **kwargs)
