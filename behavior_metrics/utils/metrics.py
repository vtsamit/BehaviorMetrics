#!/usr/bin/env python

"""This module contains the metrics manager.

This module is in charge of generating metrics for a brain execution.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""

import pandas as pd
import numpy as np
import shutil

from datetime import datetime
from bagpy import bagreader
from utils.logger import logger


def is_finish_line(point, start_point):
    try:
        current_point = np.array([point['pose.pose.position.x'], point['pose.pose.position.y']])
    except IndexError:
        current_point = point
    start_point = np.array([start_point['pose.pose.position.x'], start_point['pose.pose.position.y']])

    dist = (start_point - current_point) ** 2
    dist = np.sum(dist, axis=0)
    dist = np.sqrt(dist)
    if dist <= 1.0:
        return True
    return False


def circuit_distance_completed(checkpoints, lap_point):
    previous_point = []
    diameter = 0
    for i, point in enumerate(checkpoints):
        current_point = np.array([point['pose.pose.position.x'], point['pose.pose.position.y']])
        if i != 0:
            dist = (previous_point - current_point) ** 2
            dist = np.sum(dist, axis=0)
            dist = np.sqrt(dist)
            diameter += dist
        if point is lap_point:
            break
        previous_point = current_point
    return diameter


def read_perfect_lap_rosbag(ground_truth_lap_file):
    bag_reader = bagreader(ground_truth_lap_file)
    csv_files = []
    for topic in bag_reader.topics:
        data = bag_reader.message_by_topic(topic)
        csv_files.append(data)
    
    ground_truth_file_split = ground_truth_lap_file.split('.bag')[0]
    data_file = ground_truth_file_split + '/F1ROS-odom.csv'
    dataframe_pose = pd.read_csv(data_file)
    perfect_lap_checkpoints = []
    for index, row in dataframe_pose.iterrows():
        perfect_lap_checkpoints.append(row)

    start_point = perfect_lap_checkpoints[0]
    for x, point in enumerate(perfect_lap_checkpoints):
        if x > 100 and is_finish_line(point, start_point):
            lap_point = point
            break

    circuit_diameter = circuit_distance_completed(perfect_lap_checkpoints, lap_point)
    print('....CIRCUIT DIAMETER ----> '  + str(circuit_diameter))
    shutil.rmtree(ground_truth_lap_file.split('.bag')[0])
    return perfect_lap_checkpoints, circuit_diameter


def lap_percentage_completed(stats_filename, perfect_lap_checkpoints, circuit_diameter):
    lap_statistics = {}
    bag_reader = bagreader(stats_filename)
    csv_files = []
    for topic in bag_reader.topics:
        data = bag_reader.message_by_topic(topic)
        csv_files.append(data)

    data_file = stats_filename.split('.bag')[0] + '/F1ROS-odom.csv'
    dataframe_pose = pd.read_csv(data_file)
    checkpoints = []
    for index, row in dataframe_pose.iterrows():
        checkpoints.append(row)
    data_file = stats_filename.split('.bag')[0] + '/clock.csv'
    dataframe_pose = pd.read_csv(data_file)
    clock_points = []
    for index, row in dataframe_pose.iterrows():
        clock_points.append(row)

    end_point = checkpoints[len(checkpoints)-1]
    start_clock = clock_points[0]
    lap_statistics['completed_distance'] = circuit_distance_completed(checkpoints, end_point)
    lap_statistics['percentage_completed'] = (lap_statistics['completed_distance'] / circuit_diameter) * 100
    
    print('------------------------------------------------------------------------------------------------')
    print('COMPLETED DISTANCE ----> ' + str(lap_statistics['completed_distance']))
    print('PERCENTAGE COMPLETED -----> ' + str(lap_statistics['completed_distance'] / circuit_diameter))
    print('PERCENTAGE COMPLETED -----> ' + str(lap_statistics['percentage_completed']))
    print('CIRCUIT DIAMETER -------> ' + str(circuit_diameter))
    print('------------------------------------------------------------------------------------------------')
    
    #if lap_statistics['percentage_completed'] > 100:
    #if lap_statistics['percentage_completed'] > 80:
    lap_point = 0
    start_point = checkpoints[0]
    for ckp_iter, point in enumerate(checkpoints):
        if ckp_iter != 0 and point['header.stamp.secs'] - 10 > start_point['header.stamp.secs'] and is_finish_line(point, start_point):
            lap_point = point
            break
    print(lap_point)        
    if type(lap_point) is not int:
        seconds_start = start_clock['clock.secs']
        seconds_end = clock_points[int(len(clock_points)*(ckp_iter/len(checkpoints)))]['clock.secs']
        lap_statistics['lap_seconds'] = seconds_end - seconds_start
        lap_statistics['circuit_diameter'] = circuit_distance_completed(checkpoints, lap_point)
        lap_statistics['average_speed'] = lap_statistics['circuit_diameter']/lap_statistics['lap_seconds']
    else:
        logger.info('Lap not completed')

    shutil.rmtree(stats_filename.split('.bag')[0])
    return lap_statistics
