import datetime
import itertools

import pytz
import requests
import scrapelib
from legistar.bills import LegistarAPIBillScraper, LegistarBillScraper
from pupa.scrape import Bill, Scraper, VoteEvent
from pupa.utils import _make_pseudo_id


def sort_actions(actions):
    action_time = "MatterHistoryActionDate"
    action_name = "MatterHistoryActionName"
    sorted_actions = sorted(
        actions,
        key=lambda x: (
            x[action_time].split("T")[0],
            ACTION[x[action_name]]["order"],
            x[action_time].split("T")[1],
        ),
    )

    return sorted_actions


class CMAPBillScraper(LegistarAPIBillScraper, Scraper):
    BASE_URL = "http://webapi.legistar.com/v1/cmap"
    BASE_WEB_URL = "https://cmap.legistar.com"
    TIMEZONE = "America/Chicago"

    VOTE_OPTIONS = {
        "aye": "yes",
        "rising vote": "yes",
        "nay": "no",
        "recused": "excused",
        "not present": "absent",
    }

    def sponsorships(self, matter_id):
        for i, sponsor in enumerate(self.sponsors(matter_id)):
            sponsorship = {}
            if i == 0:
                sponsorship["primary"] = True
                sponsorship["classification"] = "Primary"
            else:
                sponsorship["primary"] = False
                sponsorship["classification"] = "Regular"

            sponsor_name = sponsor["MatterSponsorName"].strip()

            sponsorship["name"] = sponsor_name

            if "Committee" not in sponsor_name:
                sponsorship["entity_type"] = "person"
            else:
                sponsorship["entity_type"] = "organization"

            yield sponsorship

    def actions(self, matter_id):
        old_action = None
        actions = self.history(matter_id)
        actions = sort_actions(actions)

        for action in actions:
            action_date = action["MatterHistoryActionDate"]
            action_description = action["MatterHistoryActionName"]
            motion_text = action["MatterHistoryActionText"]
            responsible_org = action["MatterHistoryActionBodyName"]

            action_date = self.toTime(action_date).date()

            if responsible_org == "CMAP Board":
                responsible_org = "CMAP Board of Directors"

            bill_action = {
                "description": action_description,
                "date": action_date,
                "motion_text": motion_text,
                "organization": {"name": responsible_org},
                "classification": ACTION[action_description]["ocd"],
            }
            if bill_action != old_action:
                old_action = bill_action
            else:
                continue

            if (
                action["MatterHistoryEventId"] is not None
                and action["MatterHistoryRollCallFlag"] is not None
                and action["MatterHistoryPassedFlag"] is not None
            ):

                bool_result = action["MatterHistoryPassedFlag"]
                result = "pass" if bool_result else "fail"

                # Votes that are not roll calls, i.e., voice votes, sometimes
                # include "votes" that omit the vote option (yea, nay, etc.).
                # Capture that a vote occurred, but skip recording the
                # null votes, as they break the scraper.

                matter_history_id = action["MatterHistoryId"]
                action_text = action["MatterHistoryActionText"] or ""

                if "voice vote" in action_text.lower():
                    # while there should not be individual votes
                    # for voice votes, sometimes there are.
                    #
                    # http://webapi.legistar.com/v1/chicago/eventitems/163705/votes
                    # http://webapi.legistar.com/v1/chicago/matters/26788/histories

                    self.info(
                        "Skipping votes for history {0} of matter ID {1}".format(
                            matter_history_id, matter_id
                        )
                    )
                    votes = (result, [])
                else:
                    votes = (result, self.votes(matter_history_id))
            else:
                votes = (None, [])

            yield bill_action, votes

    def scrape(self):
        for matter in self.matters():
            matter_id = matter["MatterId"]

            date = matter["MatterIntroDate"]
            title = matter["MatterTitle"]
            identifier = matter["MatterFile"]

            bill_session = "20" + identifier.split("-")[0]
            bill_type = None

            bill = Bill(
                identifier=identifier,
                legislative_session=bill_session,
                title=title,
                classification=bill_type,
                from_organization={"name": "CMAP Board of Directors"},
            )

            legistar_web = matter["legistar_url"]

            legistar_api = "http://webapi.legistar.com/v1/chicago/matters/{0}".format(
                matter_id
            )

            bill.add_source(legistar_web, note="web")
            bill.add_source(legistar_api, note="api")

            for current, subsequent in pairwise(self.actions(matter_id)):
                action, vote = current
                motion_text = action.pop("motion_text") or action["description"]
                act = bill.add_action(**action)

                if action["description"] in {"referred", "approved and referred"}:
                    if subsequent is None:
                        body_name = matter["MatterBodyName"]
                        if body_name != "CMAP Board":
                            act.add_related_entity(
                                body_name,
                                "organization",
                                entity_id=_make_pseudo_id(name=body_name),
                            )
                    else:
                        next_action, _ = subsequent
                        next_body_name = next_action["organization"]["name"]
                        if next_body_name != "CMAP Board":
                            act.add_related_entity(
                                next_body_name,
                                "organization",
                                entity_id=_make_pseudo_id(name=next_body_name),
                            )

                result, votes = vote
                if result:
                    vote_event = VoteEvent(
                        legislative_session=bill.legislative_session,
                        motion_text=motion_text,
                        organization=action["organization"],
                        classification=action["classification"],
                        start_date=action["date"],
                        result=result,
                        bill_action=action["description"],
                        bill=bill,
                    )

                    vote_event.add_source(legistar_web)
                    vote_event.add_source(legistar_api + "/histories")

                    for vote in votes:
                        vote_value = vote["VoteValueName"]
                        if vote_value is None or vote_value.lower() in {
                            "non-voting",
                            "ex-officio",
                            "absent (nv)",
                        }:
                            continue
                        raw_option = vote_value.lower()
                        clean_option = self.VOTE_OPTIONS.get(raw_option, raw_option)
                        vote_event.vote(clean_option, vote["VotePersonName"].strip())

                    yield vote_event

            for sponsorship in self.sponsorships(matter_id):
                bill.add_sponsorship(**sponsorship)

            for topic in self.topics(matter_id):
                bill.add_subject(topic["MatterIndexName"].strip())

            for attachment in self.attachments(matter_id):
                if attachment["MatterAttachmentName"]:
                    bill.add_document_link(
                        attachment["MatterAttachmentName"],
                        attachment["MatterAttachmentHyperlink"],
                        media_type="application/pdf",
                    )

            relations = self.relations(matter_id)
            identified_relations = []
            for relation in relations:
                relation_matter_id = relation["MatterRelationMatterId"]
                try:
                    relation_matter = self.matter(relation_matter_id)
                except scrapelib.HTTPError:
                    continue
                relation_identifier = relation_matter["MatterFile"]
                try:
                    relation_date = self.toTime(relation_matter["MatterIntroDate"])
                except TypeError:
                    continue
                relation_bill_session = "20" + relation_identifier.split("-")[0]
                identified_relations.append(
                    {
                        "identifier": relation_identifier,
                        "legislative_session": relation_bill_session,
                        "date": relation_date,
                    }
                )

            if identified_relations:
                intro_date = self.toTime(date)
                relation_type = None
                if len(identified_relations) == 1:
                    if identified_relations[0]["date"] >= intro_date:
                        relation_type = "replaced-by"
                elif all(
                    relation["date"] <= intro_date for relation in identified_relations
                ):
                    relation_type = "replaces"

                if relation_type is None:
                    self.warning("Unclear relation for {0}".format(matter_id))

                else:
                    for relation in identified_relations:
                        bill.add_related_bill(
                            relation["identifier"],
                            relation["legislative_session"],
                            relation_type,
                        )

            bill.extras = {"local_classification": matter["MatterTypeName"]}

            for text in self.texts(matter_id):
                if text["MatterTextRtf"]:
                    bill.add_version_link(
                        text["MatterTextVersion"],
                        text["url"],
                        media_type="text/rtf",
                        text=text["MatterTextRtf"],
                    )
            yield bill

    def texts(self, matter_id):

        version_route = "/matters/{0}/versions"
        text_route = "/matters/{0}/texts/{1}"

        versions = self.endpoint(version_route, matter_id)

        for version in versions:
            text_url = self.BASE_URL + text_route.format(matter_id, version["Key"])
            response = self.get(text_url, stream=True)
            if int(response.headers["Content-Length"]) < 21052630:
                text_details = response.json()
                text_details["url"] = text_url
                yield text_details


def pairwise(iterable):
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.zip_longest(a, b)


ACTION = {
    "discussed": {"ocd": None, "order": 1},
    "presented": {"ocd": None, "order": 1},
    "Direct Introduction": {"ocd": "introduction", "order": 0},
    "Introduced (Agreed Calendar)": {"ocd": "introduction", "order": 0},
    "Rules Suspended - Immediate Consideration": {"ocd": "introduction", "order": 0},
    "approved and referred": {"ocd": "referral-committee", "order": 1},
    "referred": {"ocd": "referral-committee", "order": 1},
    "Re-Referred": {"ocd": "referral-committee", "order": 1},
    "Substituted in Committee": {"ocd": "substitution", "order": 1},
    "Amended in Committee": {"ocd": "amendment-passage", "order": 1},
    "withdrawn": {"ocd": "withdrawal", "order": 1},
    "Remove Co-Sponsor(s)": {"ocd": None, "order": 1},
    "Add Co-Sponsor(s)": {"ocd": None, "order": 1},
    "Recommended for Re-Referral": {"ocd": None, "order": 1},
    "Committee Discharged": {"ocd": "committee-passage", "order": 1},
    "Held in Committee": {"ocd": "committee-failure", "order": 1},
    "Recommended Do Not Pass": {"ocd": "committee-passage-unfavorable", "order": 1},
    "recommended for approval": {"ocd": "committee-passage-favorable", "order": 1},    
    "Deferred and Published": {"ocd": None, "order": 2},
    "Amended in City Council": {"ocd": "amendment-passage", "order": 2},
    "Failed to Pass": {"ocd": "failure", "order": 2},
    "approved as amended": {"ocd": "passage", "order": 2},
    "Adopted": {"ocd": "passage", "order": 2},
    "approved": {"ocd": "passage", "order": 2},
    "Passed": {"ocd": "passage", "order": 2},
    "Approved as Amended": {"ocd": "passage", "order": 2},
    "Passed as Substitute": {"ocd": "passage", "order": 2},
    "Adopted as Substitute": {"ocd": None, "order": 2},
    "read into the record": {"ocd": "filing", "order": 2},
    "received and filed": {"ocd": "filing", "order": 2},
    "received and referred": {"ocd": "committee-passage-favorable", "order": 1},
    "continued": {"ocd": "deferral", "order": 2},
    "tabled": {"ocd": "deferral", "order": 2},
    "Vetoed": {"ocd": "failure", "order": 2},
    "Published in Special Pamphlet": {"ocd": None, "order": 3},
    "Signed by Mayor": {"ocd": "executive-signature", "order": 3},
    "Repealed": {"ocd": None, "order": 4},
}
