# Requires Python 3
import httpx as requests
import locale

from typing import Dict, Tuple, List
from calendar import monthrange
from datetime import datetime


FASTLY_URL = "https://api.fastly.com/stats/usage_by_month?billable_units=true&month={month}&year={year}"
FASTLY_API_KEY = "rx9IL6PAye6GqGX5dp0zLnQ9qHqbphzG"

FASTLY_ZONES = {
    "anzac": "Australia & New Zealand",
    "asia": "Asia",
    "asia_india": "India",
    "europe": "Europe",
    "latam": "Latin America (Brazil)",
    "south_africa": "South Africa",
    "usa": "North America",
    "southamerica_std": "South America"
}

FASTLY_PRICING = {
    "anzac": {
        "gig_low": 0.171,
        "gig_high": 0.14,
        "req": 0.006
    },
    "asia": {
        "gig_low": 0.108,
        "gig_high": 0.14,
        "req": 0.006
    },
    "asia_india": {
        "gig_low": 0.252,
        "gig_high": 0.24,
        "req": 0.0128
    },
    "europe": {
        "gig_low": 0.108,
        "gig_high": 0.08,
        "req": 0.006
    },
    "latam": {
        "gig_low": 0.252,
        "gig_high": 0.24,
        "req": 0.0128
    },
    "south_africa": {
        "gig_low": 0.252,
        "gig_high": 0.24,
        "req": 0.0128
    },
    "southamerica_std": {
        "gig_low": 0.171,
        "gig_high": 0.14,
        "req": 0.0072
    },
    "usa": {
        "gig_low": 0.108,
        "gig_high": 0.08,
        "req": 0.0075
    }
}

def ascurrency(amount: float) -> str:
    return locale.currency(
        amount, 
        "$", 
        grouping=True
    )

def grab(month, year) -> Dict:
    r = requests.get(
        FASTLY_URL.format(month=month, year=year),
        headers = {
            "Fastly-Key": FASTLY_API_KEY,
        }
    )
    if r.status_code != 200:
        raise Exception("Received %d, was expecting 200" % r.status_code)

    # Response is json
    jpacket = r.json()
    if jpacket["status"] != "success":
        raise Exception("Status is not success: %s" % jpacket["status"])

    return jpacket

def calc_service(service: Dict) -> None:
    # Just look at the production avatar cache
    treq = 0.0
    tbw = 0.0
    tc = 0.0
    for region, v in service.items():
        if region == "name":
            continue

        # Get the matching region costs
        regcost = FASTLY_PRICING[region]

        # Numbers
        bw = v["bandwidth"]
        tbw += bw
        req = v["requests"]
        treq += req

        # Calculations
        creq = req * regcost["req"]
        cbw = 0.0
        if bw < 1:
            cbw = bw * regcost["gig_low"]
        else:
            clow = regcost["gig_low"]
            chigh = (bw - 1) * regcost["gig_high"]
            cbw = clow + chigh
        tc += cbw + creq

        print("""%s
    bw:         %s  (%.4f GB * %.3f/%.3f/GB)
    requests:   %s  (%s * %f/10k)
                ------
    total:      %s"""     % (
            FASTLY_ZONES[region].upper(),
            # BW
            ascurrency(cbw),
            bw,
            regcost["gig_low"],
            regcost["gig_high"],
            # Requests
            locale.currency(
                creq,
                "$",
                grouping=True
            ),
            locale.format(
                "%.2d", 
                req * 10000, 
                grouping=True
            ),
            regcost["req"],
            # Total
            locale.currency(
                creq + cbw,
                "$",
                grouping=True
            ),
        ))
    return tc


def grab_and_calc() -> None:
    today = datetime(2020, 6, 30)
    # today = datetime.today()
    month = today.month
    year = today.year
    jpacket = grab(month, year)
    services = jpacket["data"]["services"]
    print("There are %d services" % len(services.keys()))

    ts = 0.0
    for k, v in services.items():
        print("\n%s\n=========================" % v["name"])
        tsc = calc_service(v)
        ts += tsc
        print(
            "\nTotal \'%s\' Cost: %s" % ( 
                v["name"],
                locale.currency(
                    tsc, 
                    "$", 
                    grouping=True
                )
            )
        )
    print(
        "\nMONTH SPEND TO DATE: %s" % ( 
            ascurrency(ts)
        )
    )

    # Extract for month
    day_in_month = today.day
    days_in_month = monthrange(year, month)[1]
    tspace = ts/(day_in_month/days_in_month)
    print(
        "MONTH TOTAL SPEND PACE: %s" % ( 
            ascurrency(tspace)
        )
    )
    print(
        "\033[3mBased on %d/%d days in month\033[0m" % (
            day_in_month,
            days_in_month
        )
    )


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    grab_and_calc()
