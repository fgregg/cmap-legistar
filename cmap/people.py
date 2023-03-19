import collections

from legistar.people import LegistarAPIPersonScraper, LegistarPersonScraper
from pupa.scrape import Organization, Person, Scraper


class CMAPPersonScraper(LegistarAPIPersonScraper, Scraper):
    BASE_URL = "http://webapi.legistar.com/v1/cmap"
    WEB_URL = "https://cmap.legistar.com"
    TIMEZONE = "America/Chicago"

    POSTS = {
        "representing DuPage County": "Appointee of DuPage County",
        "representing Kane/Kendall Counties": "Appointee of Kane and Kendall Counties",
        "representing Lake County": "Appointee of Lake County",
        "representing McHenry County": "Appointee of McHenry County",
        "representing Will County": "Appointee of Will County",
        "representing suburban Cook County": "Appointee of Cook County outside of Chicago",
        "representing northwest Cook County": "Appointee of Cook County outside of Chicago, north of Devon",
        "representing west Cook County": "Appointee of Cook County outside of Chicago, south of devon, north of Interstate 55, and in addition the Village of Summit",
        "represents Southwest Cook County": "Appointee of Cook County outside of Chicago, south of Interstate 55, and west of Interstate 57, excluding the communities of Summit, Dixmoor, Posen, Robbins, Midlothian, Oak Forest, and Tinley Park",
        "representing south suburban Cook County": "Appointee of Cook County outside of Chicago, east of Interstate 57, and, in addition, the communities of Dixmoor, Posen, Robbins, Midlothian, Oak Forest, and Tinley Park",
        "representing City of Chicago": "Appointee of City of Chicago",
    }

    def scrape(self):
        body_types = self.body_types()

        (city_council,) = [
            body for body in self.bodies() if body["BodyName"] == "CMAP Board"
        ]

        terms = collections.defaultdict(list)
        for office in self.body_offices(city_council):
            if "vacan" not in office["OfficeRecordFullName"].lower():
                terms[office["OfficeRecordFullName"].strip()].append(office)

        web_scraper = LegistarPersonScraper(
            requests_per_minute=self.requests_per_minute
        )
        web_scraper.MEMBERLIST = "https://cmap.legistar.com/DepartmentDetail.aspx?ID=45975&GUID=88D24C6E-E96C-47BB-94D4-1179B6C45212&Search="
        web_scraper.ALL_MEMBERS = "3:3"

        if self.cache_storage:
            web_scraper.cache_storage = self.cache_storage

        if self.requests_per_minute == 0:
            web_scraper.cache_write_only = False

        web_info = {}
        for member, _ in web_scraper.councilMembers(
            {"ctl00$ContentPlaceHolder$lstName": "CMAP Board"}
        ):
            web_info[member["Person Name"]["label"]] = member

        members = {}
        for member, offices in terms.items():
            p = Person(member)
            ever_voting_member = False
            for term in offices:
                extra_text = term["OfficeRecordExtraText"]
                post_description = extra_text.split("(")[0].strip(", ")
                if post_description == "non-voting member":
                    continue
                else:
                    ever_voting_member = True

                try:
                    post_name = self.POSTS[post_description]
                except KeyError:
                    if p.name == "Maurice Cox":
                        post_name = "Appointee of City of Chicago"
                    else:
                        print(term)
                        raise

                p.add_term(
                    "Board Member",
                    "legislature",
                    district=post_name,
                    start_date=self.toDate(term["OfficeRecordStartDate"]),
                    end_date=self.toDate(term["OfficeRecordEndDate"]),
                )

            if not ever_voting_member:
                continue

            source_urls = self.person_sources_from_office(term)
            person_api_url, person_web_url = source_urls
            p.add_source(person_api_url, note="api")
            p.add_source(person_web_url, note="web")

            members[member] = p

        for body in self.bodies():
            if body["BodyTypeId"] in {
                body_types["Committees"],
                body_types["Public Bodies"],
                body_types["Policy"],
                body_types["Advisory"],
            }:
                o = Organization(
                    body["BodyName"],
                    classification="committee",
                    parent_id={"name": "CMAP Board of Directors"},
                )

                o.add_source(
                    self.BASE_URL + "/bodies/{BodyId}".format(**body), note="api"
                )
                o.add_source(
                    self.WEB_URL
                    + "/DepartmentDetail.aspx?ID={BodyId}&GUID={BodyGuid}".format(
                        **body
                    ),
                    note="web",
                )

                for office in self.body_offices(body):

                    role = office["OfficeRecordTitle"]
                    if role not in ("Vice Chair", "Chairman"):
                        role = "Member"

                    person = office["OfficeRecordFullName"].strip()
                    if person in members:
                        p = members[person]
                    else:
                        p = Person(person)

                        source_urls = self.person_sources_from_office(office)
                        person_api_url, person_web_url = source_urls
                        p.add_source(person_api_url, note="api")
                        p.add_source(person_web_url, note="web")

                        members[person] = p

                    try:
                        end_date = self.toDate(office["OfficeRecordEndDate"])
                    except TypeError:
                        end_date = ""
                    p.add_membership(
                        body["BodyName"],
                        role=role,
                        start_date=self.toDate(office["OfficeRecordStartDate"]),
                        end_date=end_date,
                    )

                yield o

        for p in members.values():
            yield p
