from pupa.scrape import Jurisdiction, Organization

from .bills import CMAPBillScraper

# from .events import CMAPEventsScraper
from .people import CMAPPersonScraper


class CMAP(Jurisdiction):
    # not quite right, but pretty close
    division_id = "ocd-division/country:us/state:il/county:cook"

    # also not quite right.
    classification = "government"

    name = "Chicago Metropolitan Agency for Planning"
    url = "https://www.cmap.illinois.gov/"

    scrapers = {
        "people": CMAPPersonScraper,
        #        "events": CMAPEventsScraper,
        "bills": CMAPBillScraper,
    }

    legislative_sessions = []
    # check to see when their calendar begins
    for year in range(2022, 2024):
        session = {
            "identifier": "{}".format(year),
            "start_date": "{}-01-01".format(year),
            "end_date": "{}-12-31".format(year + 1),
        }
        legislative_sessions.append(session)

    def get_organizations(self):
        org = Organization(name="CMAP Board of Directors", classification="legislature")
        org.add_post(
            "Appointee of DuPage County",
            "Board Member",
            division_id="ocd-division/country:us/state:il/county:dupage",
        )

        org.add_post(
            "Appointee of Kane and Kendall Counties",
            "Board Member",
            division_id="ocd-division/country:us/state:il/county:kane",
        )

        org.add_post(
            "Appointee of Lake County",
            "Board Member",
            division_id="ocd-division/country:us/state:il/county:lake",
        )

        org.add_post(
            "Appointee of McHenry County",
            "Board Member",
            division_id="ocd-division/country:us/state:il/county:mchenry",
        )

        org.add_post(
            "Appointee of Will County",
            "Board Member",
            division_id="ocd-division/country:us/state:il/county:will",
        )

        org.add_post(
            "Appointee of Cook County outside of Chicago",
            "Board Member",
            division_id="ocd-division/country:us/state:il/county:cook",
        )

        org.add_post(
            "Appointee of Cook County outside of Chicago, north of Devon",
            "Board Member",
            division_id="ocd-division/country:us/state:il/county:cook",
        )

        org.add_post(
            "Appointee of Cook County outside of Chicago, south of devon, north of Interstate 55, and in addition the Village of Summit",
            "Board Member",
            division_id="ocd-division/country:us/state:il/county:cook",
        )

        org.add_post(
            "Appointee of Cook County outside of Chicago, south of Interstate 55, and west of Interstate 57, excluding the communities of Summit, Dixmoor, Posen, Robbins, Midlothian, Oak Forest, and Tinley Park",
            "Board Member",
            division_id="ocd-division/country:us/state:il/county:cook",
        )

        org.add_post(
            "Appointee of Cook County outside of Chicago, east of Interstate 57, and, in addition, the communities of Dixmoor, Posen, Robbins, Midlothian, Oak Forest, and Tinley Park",
            "Board Member",
            division_id="ocd-division/country:us/state:il/county:cook",
        )

        org.add_post(
            "Appointee of City of Chicago",
            "Board Member",
            division_id="ocd-division/country:us/state:il/place:chicago",
        )

        yield org
