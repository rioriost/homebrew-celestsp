#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import pandas as pd
import networkx as nx
from scipy.spatial import distance_matrix
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy import units as u
import numpy as np
import os
import sys
import requests
import matplotlib.pyplot as plt


def read_celestial_names(file_path: str = "") -> pd.DataFrame:
    """
    Read celestial coordinates from a file.

    Args:
        file_path (str): Path to the file.

    Returns:
        np.ndarray: Array of celestial coordinates.
    """

    if os.path.exists(file_path) is False:
        print(f"Input file {file_path} does not exist.")
        sys.exit(1)

    with open(file_path, "r") as f:
        ra_degs = []
        for line in f.readlines():
            name = line.replace("\n", "")
            try:
                coord = SkyCoord.from_name(name)
                ra_degs.append({"Name": name, "RA": coord.ra.deg, "Dec": coord.dec.deg})
            except Exception as e:
                print(f"Error: {e}")
                continue
    df = pd.DataFrame(ra_degs)
    if df.empty:
        print("Input file is empty.")
        sys.exit(1)

    return df


def make_graph(coordinates: np.ndarray = None, dist_matrix: list = []) -> nx.Graph:
    """
    Create a graph from celestial coordinates.

    Args:
        coordinates (np.ndarray): Array of celestial coordinates.
        dist_matrix (list): Distance matrix.

    Returns:
        nx.Graph: Graph representing the celestial coordinates.
    """

    G = nx.Graph()

    for i, (ra, dec) in enumerate(coordinates):
        G.add_node(i, pos=(ra, dec))

    for i in range(len(coordinates)):
        for j in range(i + 1, len(coordinates)):
            G.add_edge(i, j, weight=dist_matrix[i, j])

    return G


def find_westernmost_body(
    df: pd.DataFrame = None,
    observation_time: Time = None,
    location: EarthLocation = None,
):
    """
    Find the celestial body closest to the western direction (270 degrees azimuth, 0 degrees altitude).

    Args:
        df (pd.DataFrame): DataFrame containing celestial coordinates.
        observation_time (Time): Observation time.
        location (EarthLocation): Observation location.

    Returns:
        int: Index of the celestial body closest to the western direction.
    """

    altaz_frame = AltAz(obstime=observation_time, location=location)
    closest_distance = np.inf
    closest_index = -1

    altitudes = []
    azimuths = []
    observables = []
    for i, row in df.iterrows():
        sky_coord = SkyCoord(ra=row["RA"], dec=row["Dec"], unit="deg")
        altaz_coord = sky_coord.transform_to(altaz_frame)
        altitudes.append(altaz_coord.alt.deg)
        azimuths.append(altaz_coord.az.deg)
        observables.append(is_observable(altaz_coord))

        # Calculate the distance to (270 degrees azimuth, 0 degrees altitude)
        azimuth_diff = abs(altaz_coord.az.deg - 270)
        altitude_diff = abs(altaz_coord.alt.deg - 0)
        distance = np.sqrt(azimuth_diff**2 + altitude_diff**2)

        if distance < closest_distance:
            closest_distance = distance
            closest_index = i

    df["Altitude"] = altitudes
    df["Azimuth"] = azimuths
    df["Observable"] = observables

    return closest_index


def is_observable(altaz_coord, min_altitude=0):
    """
    Check if a celestial body is observable.

    Args:
        altaz_coord (AltAz): AltAz coordinates of the celestial body.
        min_altitude (float): Minimum altitude for the celestial body to be observable.

    Returns:
        bool: True if the celestial body is observable, False otherwise.
    """

    return altaz_coord.alt.deg > min_altitude


def get_location() -> tuple:
    """
    Get the current location of the user.

    Returns:
        tuple: Latitude and longitude of the current location.
    """

    try:
        response = requests.get("http://ip-api.com/json/")
        data = response.json()

        if data["status"] == "success":
            latitude = data["lat"]
            longitude = data["lon"]
            return float(latitude), float(longitude)
        else:
            print("Error: Unable to get location data")
            return None, None
    except Exception as e:
        return None, None


def set_args() -> argparse.Namespace:
    """
    Set up command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """

    latitude, longitude = get_location()
    datetime = Time.now().iso.split(".")[0].replace("T", " ").split(" ")
    parser = argparse.ArgumentParser(description="ARC TSP")
    parser.add_argument(
        "input", type=str, help="Input file path containing celestial coordinates."
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=latitude if latitude is not None else 0,
        help="Latitude of the observation location.",
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=longitude if longitude is not None else 0,
        help="Longitude of the observation location.",
    )
    parser.add_argument(
        "--height", type=float, default=0, help="Height of the observation location."
    )
    parser.add_argument(
        "--date",
        type=str,
        default=datetime[0],
        help="Observation date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--time",
        type=str,
        default=datetime[1],
        help="Observation time in HH:MM:SS format.",
    )
    parser.add_argument(
        "--tz",
        type=str,
        default="+9",  # JST
        help="Time zone for observation date/time.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results.png",
        help="Filename for the output image.",
    )
    args = parser.parse_args()
    args.default_datetime = args.date == datetime[0] and args.time == datetime[1]
    return args


def show_results(df: pd.DataFrame = None) -> None:
    """
    Show the results of the TSP calculation.
    Args:
        df (pd.DataFrame): DataFrame containing celestial coordinates and their order.
    """

    print("\nOptimal Order of Celestial Bodies:")
    for i, row in df.iterrows():
        if i + 1 == len(df):
            break
        name = row["Name"]
        ra = f"{row['RA']:.2f}"
        dec = f"{row['Dec']:.2f}"
        alt = f"{row['Altitude']:.2f}"
        azimuth = f"{row['Azimuth']:.2f}"
        obs = row["Observable"]
        print(
            f"Name: {name},{' '*(7-len(name))} RA: {ra},{' '*(7-len(ra))}Dec:{dec},{' '*(6-len(dec))}Altitude:{alt},{' '*(7-len(alt))}Azimuth:{azimuth},{' '*(7-len(azimuth))}Observable: {obs}"
        )


def save_spherical_image(
    df: pd.DataFrame,
    location_str: str = "",
    observation_time: Time = None,
    filename: str = "spherical_results.png",
) -> None:
    """
    Save the results of the TSP calculation as a spherical image.

    Args:
        df (pd.DataFrame): DataFrame containing celestial coordinates and their order.
        location (str): Observation location as a string.
        observation_time (Time): Observation time.
        filename (str): Filename for the output image.
    """
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection="polar")

    # Convert Azimuth to radians for polar plot
    az_radians = np.deg2rad(df["Azimuth"])
    alt_radians = np.deg2rad(90 - df["Altitude"])  # Convert Altitude to colatitude

    # Plot the celestial coordinates
    ax.scatter(az_radians, alt_radians, c="blue", label="Celestial Bodies")

    # Annotate each point with its name
    for i, row in df.iterrows():
        ax.annotate(
            row["Name"], (az_radians[i], alt_radians[i]), fontsize=8, ha="right"
        )

    # Plot the path
    for i in range(len(df) - 1):
        start_az = az_radians[i]
        start_alt = alt_radians[i]
        end_az = az_radians[i + 1]
        end_alt = alt_radians[i + 1]
        ax.plot([start_az, end_az], [start_alt, end_alt], "r-")

    # Add an arrow and label for the starting point
    start_az = az_radians[0]
    start_alt = alt_radians[0]
    ax.annotate(
        "Start",
        xy=(start_az, start_alt),
        xytext=(start_az, start_alt + 0.1),
        fontsize=12,
        color="green",
        ha="center",
    )

    # Add an arrow for the direction from the start to the second point
    if len(df) > 1:
        second_az = az_radians[1]
        second_alt = alt_radians[1]
        ax.annotate(
            "",
            xy=(second_az, second_alt),
            xytext=(start_az, start_alt),
            arrowprops=dict(facecolor="red", arrowstyle="->", lw=2.5),
        )

    # Add labels and title
    ax.set_title("Optimal Order of Celestial Bodies (Spherical Projection)", pad=30)
    ax.set_theta_zero_location("N")  # Set 0 degrees to the top (North)
    ax.set_theta_direction(-1)  # Set the direction of increasing angles to clockwise

    # Add observation location and time at the bottom of the image
    if observation_time is not None:
        observation_time_str = observation_time.iso
    else:
        observation_time_str = "Unknown"

    fig.text(
        0.5,
        0.01,
        f"Location: {location_str} | Observation Time: {observation_time_str}",
        ha="center",
        fontsize=10,
    )

    # Save the plot as an image file
    plt.savefig(filename)
    plt.close()


def main():
    RED = "\033[31m"
    RESET = "\033[0m"

    args = set_args()

    df = read_celestial_names(args.input)
    coordinates = df[["RA", "Dec"]].to_numpy()
    dist_matrix = distance_matrix(coordinates, coordinates)

    print(f"Location: Lat: {args.lat}, Lon: {args.lon}, {args.height}m")
    location = EarthLocation(lat=args.lat, lon=args.lon, height=args.height)
    location_str = f"Lat: {args.lat}, Lon: {args.lon}, Height: {args.height}m"
    print(f"Observation Date/Time: {args.date} {args.time} {args.tz}")
    if args.default_datetime:
        observation_time = Time(f"{args.date} {args.time}")

    else:
        observation_time = Time(f"{args.date} {args.time}") - int(args.tz) * u.hour

    westernmost_index = find_westernmost_body(
        df=df, observation_time=observation_time, location=location
    )

    if not df["Observable"].all():
        print(f"\n{RED}Some celestial bodies are NOT observable!!{RESET}")

    if westernmost_index != -1:
        G = make_graph(coordinates=coordinates, dist_matrix=dist_matrix)
        tsp_path = nx.approximation.greedy_tsp(G, source=westernmost_index)
        df_ordered = df.iloc[tsp_path].reset_index(drop=True)
        show_results(df=df_ordered)
        save_spherical_image(
            df=df_ordered,
            location_str=location_str,
            observation_time=observation_time,
            filename=args.output,
        )
    else:
        print("Could not find the westernmost celestial body.")


if __name__ == "__main__":
    main()
