# -*- coding: utf-8 -*-
# Author: WILL_V

from icalendar import Calendar, Event
from datetime import datetime, timezone
import requests
import yaml
from copy import deepcopy
from datetime import datetime, timezone, timedelta

def parse_tz(tz):
    if tz == "AoE":
        return "-1200"
    elif tz.startswith("UTC-"):
        return "-{:02d}00".format(int(tz[4:]))
    elif tz.startswith("UTC+"):
        return "+{:02d}00".format(int(tz[4:]))
    else:
        return "+0000"

def get_conf_data():
    yml_str = requests.get(
        "https://ccfddl.github.io/conference/allconf.yml").content.decode("utf-8")
    all_conf = yaml.safe_load(yml_str)

    all_conf_ext = []
    now = datetime.now(tz=timezone.utc)
    for conf in all_conf:
        for c in conf["confs"]:
            cur_conf = deepcopy(conf)
            cur_conf["title"] = cur_conf["title"] + str(c["year"])
            cur_conf.update(c)
            time_obj = None
            tz = parse_tz(c["timezone"])
            for d in c["timeline"]:
                try:
                    cur_d = datetime.strptime(
                        d["deadline"] + " {}".format(tz), '%Y-%m-%d %H:%M:%S %z')
                    if cur_d < now:
                        continue
                    if time_obj is None or cur_d < time_obj:
                        time_obj = cur_d
                except Exception as e:
                    pass
            if time_obj is not None:
                time_obj = time_obj.astimezone(timezone(timedelta(hours=8)))
                cur_conf["time_obj"] = time_obj
                if time_obj > now:
                    all_conf_ext.append(cur_conf)

    all_conf_ext = sorted(all_conf_ext, key=lambda x: x['time_obj'])
    return all_conf_ext

def conf_filter(filter=None):
    def alpha_id(with_digits):
        return ''.join(char for char in with_digits.lower() if char.isalpha())

    # table = [["Title", "Sub", "Rank", "DDL", "Link", "Time"]]
    table = []
    if filter is None:
        filter = {
            "conf": [],
            "rank": "ABC",
            "sub": "",
            "remove": {}
            }


    def add_table(x):
        sc_match = {"DS": "计算机体系结构/并行与分布计算/存储系统",
                    "NW": "计算机网络",
                    "SC": "网络与信息安全",
                    "SE": "软件工程/系统软件/程序设计语言",
                    "DB": "数据库/数据挖掘/内容检索",
                    "CT": "计算机科学理论",
                    "CG": "计算机图形学与多媒体",
                    "AI": "人工智能",
                    "HI": "人机交互与普适计算",
                    "MX": "交叉/综合/新兴",
                    }
        x["sub"] = sc_match.get(x["sub"]) if sc_match.get(
            x["sub"]) else x["sub"]
        return [x["title"],
                x["sub"],
                x["rank"],
                # format_duraton(x["time_obj"], now),
                x["link"],
                x["time_obj"],
                x["place"],
                ]

    for x in get_conf_data():
        confs = [conf.lower() for conf in filter["conf"]]
        x.update({"rank": x["rank"].get("ccf")})
        if alpha_id(x["id"]) in confs:
            table.append(add_table(x))
        elif alpha_id(x["sub"]) in filter["sub"].lower():
            table.append(add_table(x))
        elif alpha_id(x["rank"]) in filter["rank"].lower():
            table.append(add_table(x))
    for r in filter.get("remove").keys():
        for i in range(len(table)-1, 0, -1):
            if r.lower() == "conf":
                if table[i][0] == filter.get("remove")[r]:
                    table.pop(i)
            if r.lower() == "sub":
                if table[i][1] == filter.get("remove")[r]:
                    table.pop(i)
            if r.lower() == "rank":
                if table[i][2] == filter.get("remove")[r]:
                    table.pop(i)
    return table

def get_ics(filter=None):
    cal = Calendar()
    cal.add('prodid', '-//CCF Ranking//willv//')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('X-WR-CALNAME', 'CCF_Ranking')
    cal.add('X-WR-TIMEZONE', 'Asia/Shanghai')
    for x in conf_filter(filter=filter):
        event = Event()
        event.add('summary', f"{x[0]} ({x[1]} CCF-{x[2]})")
        ddl = x[4]
        dtstart = ddl.replace(hour=0, minute=0, second=0, microsecond=0)
        event.add('dtstart', dtstart)
        event.add('dtend', ddl)
        event.add('dtstamp', datetime.now())
        event['location'] = x[5]
        event['uid'] = x[3]
        cal.add_component(event)
    return cal.to_ical()

def write_ics(filter=None):
    if filter is not None:
        with open("ccf_filter.ics", "wb") as f:
            f.write(get_ics(filter=filter))
    with open("ccf.ics", "wb") as f:
        f.write(get_ics(filter=None))

def read_ics():
    with open("ccf.ics", "rb") as g:
        gcal = Calendar.from_ical(g.read())
        for component in gcal.walk():
            if component.name == "VEVENT":
                print(component.get('summary'))
                print(component.get('dtstart'))
                print(component.get('dtend'))
                print(component.get('dtstamp'))
                print(component.get('location'))
                print(component.get('uid'))

if __name__=='__main__':
    filter = {
    "conf": ["SP","CSS","USS","NDSS"],
    "rank": "A",
    "sub":"SC",
    "remove": {"rank":"C"}
    }
    write_ics(filter=filter)
    read_ics()