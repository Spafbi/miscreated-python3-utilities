#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# title           : logs_parse.py
# description     : Methods for parsing chat or damage logs
#                   This methods in this script are intended to be imported into
#                   another Python script.
# author          : Chris Snow - (aka Spafbi)
# python_version  : 3.9.1
# ===================================================
import hashlib


def chat_line(line, filedate=None, hash_fieldname='_id'):
    '''
    Parse a line from the Miscrated chat log
    :param string: a line from a Miscreated chat log
    :return: a dictionary of the line's fields and values
    '''
    c = dict()

    line = line.rstrip('\r\n')
    c['raw'] = line
    if filedate is None:
        c['entry_time'] = line[1:9]
    else:
        c['entry_time'] = '{} {}'.format(filedate, line[1:9])
    c['steam_id'] = line[20:37]
    chunk = line[45:].split('] [IP ', 1)
    c['player_name'] = chunk[0].strip()
    chunk = chunk[1].split(':', 1)
    c['ip_address'] = chunk[0]
    try:
        c['message'] = chunk[1].split('] ')[1].strip()
    except:
        c['message'] = ''
    return c


def damage_line(line, filedate=None, hash_fieldname='_id'):
    '''
    Parse a line from the Miscrated damage log
    :param string: a line from a Miscreated damage log
    :return: a dictionary of the line's fields and values
    '''

    d = dict()
    line = line.rstrip('\r\n')
    d['raw'] = line

    if filedate is None:
        d['timestamp'] = line[1:13]
    else:
        d['timestamp'] = '{} {}'.format(filedate, line[1:13])
    d['entry_time'] = line[1:13]
    # d['damage_time'] = line[1:9]
    # d['damage_time_microseconds'] = line[10:13]
    chunk = line.split('] [TOD: ', 1)[1].split('] ', 1)
    d['time_of_day'] = chunk[0]
    chunk = chunk[1].split(' - ', 1)
    d['event_type'] = chunk[0]
    chunk = chunk[1]
    while (chunk.find(': "') > 0):
        field = chunk[:chunk.find(': "')].strip()
        remainder = chunk[chunk.find(': "') + 3:].strip()

        # ** extract values ** #
        # We have to use a different "find" string for fields using
        # user-defined player names
        if field == 'shooterName':
            d['shooter_name'] = shooter_name_value(d['event_type'], remainder)
        elif field == 'driverName':
            value = remainder[:remainder.find('", driver')]
            d['driver_name'] = value.strip()
        elif field == 'targetName':
            d['target_name'] = target_name_value(d['event_type'], remainder)
        elif field == 'projectile':
            value = remainder[:remainder.find('", ')].replace('ammo_', '')
            d['projectile'] = value.strip()
        elif field == 'damage':
            value = remainder[:remainder.find('", ')]
            d['raw_damage'] = value.strip()
            if value.find('x*') > 1:
                value = value.replace('x', '').replace('=', '*').strip()
                d['damage_unscaled'], \
                    d['damage_equipment_multiplier'], \
                    d['damage_body_multiplier'], \
                    d['damage_faction_multiplier'], \
                    d['damage_total'] = value.split('*')
            else:
                d['damage_total'] = value.strip()
        else:
            value = remainder[:remainder.find('", ')]
            known_fields = {
                'hitType': 'hit_type',
                'shooterFaction': 'shooter_faction',
                'shooterPos': 'shooter_position',
                'shooterSteamID': 'shooter_steam_id',
                'targetFaction': 'target_faction',
                'targetPos': 'target_position',
                'targetSteamID': 'target_steam_id'
            }
            fieldname = known_fields.get(field, field)
            d[fieldname] = value.strip()

        # extract position components
        if field in ('targetPos', 'shooterPos'):
            fieldname = determine_pos_field_prefix(field)
            d[fieldname + 'X'], d[fieldname + 'Y'], d[fieldname + 'Z'] = \
                value.split(',')

        # extract 'part' data
        if field == 'part':
            d['part_number'] = value[0:value.find('(')]
            d['part_description'] = (
                value[value.find('(') + 1:value.find(')')].
                replace('Bip01 ', '').
                replace('Def_', '')
            )

        # pops off the data we just processed
        chunk = remainder[remainder.find('", ') + 3:]

    entry_time_hr = int(d['entry_time'][:2])
    entry_time_min = round(int(d['entry_time'][3:8].replace(':', ''))/1000)
    if entry_time_min == 6:
        entry_time_hr = entry_time_hr + 1
        if entry_time_hr == 24:
            entry_time_mod = "0.0"
        else:
            entry_time_mod = "{}.{}".format(entry_time_hr, 0)
    else:
        entry_time_mod = "{}.{}".format(entry_time_hr, entry_time_min)
    this_target_name = str(d.get('target_name', ''))
    this_entry_time_mod = str(entry_time_mod)
    this_target_position_X = str(d.get('target_position_X', '00'))[:2]
    this_target_position_Y = str(d.get('target_position_Y', '00'))[:2]
    this_target_position_Z = str(d.get('target_position_Z', '00'))[:1]
    string = "{0}{1}{2}{3}{4}".format(this_target_name,
                                      this_entry_time_mod,
                                      this_target_position_X,
                                      this_target_position_Y,
                                      this_target_position_Z)
    if filedate is not None:
        string += filedate
    d['digest'] = hashlib.md5(string.encode()).hexdigest()
    return d


def determine_pos_field_prefix(field):
    if field == 'targetPos':
        fieldname = 'target_position_'
    else:
        fieldname = 'shooter_position_'
    return fieldname


def shooter_name_value(event_type, remainder):
    if event_type == 'explosion':
        value = remainder[:remainder.find('", target')]
    else:
        value = remainder[:remainder.find('", shooter')]
    return value.strip()


def target_name_value(event_type, remainder):
    if event_type == 'explosion':
        value = remainder[:remainder.find('", weapon')]
    else:
        value = remainder[:remainder.find('", target')]
    return value.strip()
