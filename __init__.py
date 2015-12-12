#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2015 Thomas Ernst                            offline@gmx.net
#########################################################################
#  This file is part of SmartHome.py.
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################
import logging
import datetime

logger = logging.getLogger()


class Meter:
    # Constructor
    # smarthome: instance of smarthome.py
    # startup_delay_default: default startup delay
    # manual_break_default: default break after manual changes of items
    # log_level: loglevel for extended logging
    # log_directory: directory for extended logging files
    def __init__(self, smarthome, dateformat="%d.%m.%Y", timeformat="%H:%M:%S"):
        self.alive = False
        self.__sh = smarthome
        self.__meters = {}
        self.__dateformat = dateformat
        self.__timeformat = timeformat

    # Parse an item
    # item: item to parse
    def parse_item(self, item):
        # leave if this is not an meter item
        if "meter_tick" not in item.conf:
            return None

        try:
            # Create meter object and add to dictionary
            item_meter = MeterObject(self.__sh, item)
            self.__meters[item_meter.id] = item_meter
            return None

        except ValueError as ex:
            logger.error(ex)
            return None

    # Initialization of plugin
    def run(self):
        incomplete = []
        for name, meter in self.__meters.items():
            if not meter.complete():
                incomplete.append(name)
        for name in incomplete:
            del self.__meters[name]

        if len(self.__meters) > 0:
            logger.info("Using Meter-Plugin for {} meters".format(len(self.__meters)))
        else:
            logger.info("Meter-Plugin deactivated because no meters have been found.")

        self.alive = True

    # Stopping of plugin
    def stop(self):
        self.alive = False

    # Determinage usage of certain meter
    # meter_id: Id of meter (item)
    # start: How far in the past to start?
    # lengh: How long?
    # from_item: Item to write start datetime
    # to_item: Item to write end datetime
    # start and length can be given as #[d|w|m|y]
    # All intervals always start at 00:00:00 and end at 23:59:59
    def get_usage(self, meter_id, start, length, from_item=None, to_item=None):
        meter = self.__find_meter(meter_id)
        if meter is None:
            return None

        start, end = self.__fullday_interval(start, length)
        if start == 0 or end == 0:
            return None

        if from_item is not None:
            from_item = self.__sh.return_item(from_item)
            if from_item is not None:
                from_item(start.strftime(self.__dateformat))

        if to_item is not None:
            to_item = self.__sh.return_item(to_item)
            if to_item is not None:
                to_item(end.strftime(self.__dateformat))

        return meter.get_usage(start, end)

    # find certain meter object and return it
    def __find_meter(self, meter_id):
        if meter_id in self.__meters:
            return self.__meters[meter_id]
        else:
            logger.error("Meter '{0}' not found!".format(meter_id))
            return None

    # calculate start and end date based on start and length information
    # start: How far in the past to start?
    # lengh: How long?
    def __fullday_interval(self, start, length):
        start = self.__get_days(start)
        length = self.__get_days(length)
        if start is None or length is None:
            return 0, 0
        end = start - (length - 1)

        now = self.__sh.now().date()
        startdate = now - datetime.timedelta(days=start)
        enddate = now - datetime.timedelta(days=end)
        starttime = datetime.datetime.combine(startdate, datetime.time.min)
        endtime = datetime.datetime.combine(enddate, datetime.time.max)

        return starttime, endtime

    # Calculate number of days
    # value: #[d|w|m|y]
    @staticmethod
    def __get_days(value):
        if isinstance(value, int):
            return value
        elif isinstance(value, str):
            try:
                if value.endswith("d"):
                    return int(value[:-1])
                elif value.endswith("w"):
                    return int(value[:-1]) * 7
                elif value.endswith("m"):
                    return int(value[:-1]) * 30
                elif value.endswith("y"):
                    return int(value[:-1]) * 365
                else:
                    return int(value)
            except ValueError:
                logger.error("Invalid interval '{0}'. Allowed is '#[d|w|m|y]'.".format(value))
                return None
        else:
            logger.error("Invalid interval '{0}'. Allowed is '#[d|w|m|y]'.".format(value))
            return None


class MeterObject:
    # Id of meter
    @property
    def id(self):
        return self.__id

    # Id of meter
    @property
    def name(self):
        return self.__value_item.name

    # Constructor
    # smarthome: Instance of smarthome.py
    # value item: Item containing meter value
    def __init__(self, smarthome, value_item):
        self.__sh = smarthome
        self.__value_item = value_item
        self.__id = self.__value_item.id()
        self.__tick = None
        self.__increment = 1
        self.__power = None
        self.__power_list = []

    def get_usage(self, start: datetime.datetime, end: datetime.datetime):
        start_ts = start.timestamp() * 1000
        end_ts = end.timestamp() * 1000

        min_value = self.__value_item.db("min", start_ts, end_ts)
        max_value = self.__value_item.db("max", start_ts, end_ts)
        min_value = 0 if min_value is None else min_value
        max_value = 0 if max_value is None else max_value
        return max_value - min_value

    # Complete initialization after all items have been parsed
    def complete(self):
        tick_item = self.__value_item.conf["meter_tick"]
        self.__tick = self.__sh.return_item(tick_item)
        if self.__tick is None:
            text = "Item {0}: Item {1} given as 'meter_tick' not found. Meter will be disabled!"
            logger.error(text.format(self.__value_item.id(), tick_item))
            return False
        self.__tick.add_method_trigger(self.tick)

        if "meter_increment" in self.__value_item.conf:
            self.__increment = float(self.__value_item.conf["meter_increment"])

        if "meter_power" in self.__value_item.conf:
            power_item = self.__value_item.conf["meter_power"]
            self.__power = self.__sh.return_item(power_item)
            if self.__power is None:
                text = "Item {0}: Item {1} given as 'meter_power' not found. Power will not be avaialble!"
                logger.error(text.format(self.__value_item.id(), self.__power))
                self.__power = None
                power_item = "(not found)"
        else:
            power_item = "(not available)"

        text = "Meter '{0}' Initialized: Increment {1}, Tick from {2}, Value in {3}, Power in {4}"
        logger.info(text.format(self.__id, self.__increment, tick_item, self.__value_item.id(), power_item))
        return True

    # Handle meter tick
    # noinspection PyUnusedLocal
    def tick(self, item, caller=None, source=None, dest=None):
        self.__value_item(self.__value_item() + self.__increment)
        if self.__power is not None:
            power = max(3600 * self.__increment / self.__tick.prev_age(), 0)
            self.__power_list.append(power)
            while len(self.__power_list) > 10:
                self.__power_list.pop(0)
            power_sum = sum(self.__power_list)
            power_len = float(len(self.__power_list))
            # noinspection PyCallingNonCallable
            self.__power(power_sum / power_len)
