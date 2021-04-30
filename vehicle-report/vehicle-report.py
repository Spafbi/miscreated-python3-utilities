from pathlib import Path
import csv
import logging
import math
import os
import sqlite3
import sys


def calc_distance(x1, y1, x2, y2):
    """Calculates the distance between two objects on a plane

    Args:
        x1 (float): X position value for object 1
        y1 (float): Y position value for object 1
        x2 (float): X position value for object 2
        y2 (float): Y position value for object 2

    Returns:
        float: [description]
    """
    dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    return dist


def get_bases_sql():
    """SQL command to look up all bases

    Returns:
        string: SQL command
    """
    sql = """
        SELECT (AccountID + 76561197960265728) AS Owner,
            ROUND(PosX,5) AS PosX,
            ROUND(PosY,5) AS PosY
        FROM Structures
        WHERE ClassName='PlotSign'
        """
    return sql


def get_plotsign_owning_vehicle(bases, vehiclesPosX, vehiclePosY):
    for plotsign in bases:
        steamID64, basePosX, basePosY = plotsign
        distance = calc_distance(vehiclesPosX, vehiclePosY, basePosX, basePosY)
        if distance <= 30:
            return steamID64
    
    return False


def get_vehicle_ownership(bases, vehicles):
    """Loops throught the bases and vehicles result sets to identify vehicles
       located within 30m of a base's plot sign, and which vehicles are
       outside of that range

    Args:
        bases (list): A list of lists - each embedded list should contain: (SteamID64, PosX, PosY)
        vehicles (list): A list of lists - each embedded list should contain: (VehicleID, VehicleClass, PosX, PosY)
    
    Returns:
        vehicleOwnership (dictionary): vehicleID as key, with owner, vehicleClass, vehiclesPosX, vehiclePosY
    """
    vehicleOwnership = dict()
    for vehicle in vehicles:
        vehicleID, vehicleClass, vehiclesPosX, vehiclePosY = vehicle
        vehicle_ownership = get_plotsign_owning_vehicle(bases, vehiclesPosX, vehiclePosY)

        vehicleOwnership[vehicleID] = {
            "owner": vehicle_ownership,
            "vehicleClass": vehicleClass.replace('_', ' ').capitalize(),
            "vehiclesPosX": round(vehiclesPosX),
            "vehiclePosY": round(vehiclePosY)
        }

    return vehicleOwnership


def get_result_set(db, sql):
    """The executes a passed SQL command and returns a result set. If
        INSERT or UPDATE is detected, a write is assumed and a commit is
        also performed.

    Args:
        sql (string): SQL command

    Returns:
        list: a result set resulting from the execution of the SQL command
    """
    if not os.path.exists(db):
        logging.info('Database does not exist')
        return False

    logging.debug(sql)

    # If 'insert ' or 'update ' exist in the sql statement, we're probably
    # doing a database write and will want to commit the changes.
    commit = (sql.lower().find('insert ') >= 0) or \
                (sql.lower().find('update ') >= 0)

    conn = sqlite3.connect(db)
    c = conn.cursor()
    try:
        results = c.execute(sql)
        if commit:
            conn.commit()
    except sqlite3.Error as e:
        print(e)
        return list()
        
    result_set = list()
    for result in results.fetchall():
        result_set.append(result)

    return result_set


def get_vehicles_sql():
    """SQL command to look up all vehicles

    Returns:
        string: SQL command
    """
    sql = """
        SELECT VehicleID,
            ClassName,
            ROUND(PosX,5) AS PosX,
            ROUND(PosY,5) AS PosY
        FROM Vehicles
        """
    return sql


def main():
    """
    Summary: Default method if this module is run as __main__.
    """
    logging.basicConfig(level=logging.INFO)

    script_path = os.path.abspath(os.path.dirname(sys.argv[0]))

    # Check to see if the path includes a space and exit if it does
    if script_path.find(' ') >= 0:
        logging.info('This script cannot be run in paths having spaces. Current path: {}'.format(script_path))
        exit(1)
    
    database = Path("{}/miscreated.db".format(script_path))

    if not os.path.exists(database):
        logging.info('The "miscreated.db" file does not exist in this path: {}'.format(database))
        exit(1)

    # Get our bases and vehicles
    bases=get_result_set(database, get_bases_sql())
    vehicles=get_result_set(database, get_vehicles_sql())

    # Calculate who owns each vehicle
    vehicleOwnership = get_vehicle_ownership(bases, vehicles)

    # Clear the screen
    os.system('cls')

    # Output vehicle ownership
    logging.info('Owned vehicles:')
    atLeastOneOwned = False

    for vehicle, values in vehicleOwnership.items():
        owner = values.get('owner')
        if owner:
            atLeastOneOwned = True
            vehicleClass=values.get('vehicleClass')
            vehiclesPosX=values.get('vehiclesPosX')
            vehiclePosY=values.get('vehiclePosY')
            logging.info('{} is owned by {}: ({}, {})'.format(vehicleClass, owner, vehiclesPosX, vehiclePosY))

    if not atLeastOneOwned:
        logging.info('No vehicles are located at player bases')


if __name__ == '__main__':
    main()