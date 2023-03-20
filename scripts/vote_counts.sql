BEGIN;

DELETE FROM opencivicdata_votecount;

INSERT INTO opencivicdata_votecount
SELECT substr(lower(hex(randomblob(4))),1,8) || '-' ||
       substr(lower(hex(randomblob(2))),1,4) || '-4' ||
       substr(lower(hex(randomblob(2))),1,3) || '-a' ||
       substr(lower(hex(randomblob(2))),1,3) || '-' ||
       substr(lower(hex(randomblob(6))),1,12),
       option,
       count(*),
       vote_event_id
FROM opencivicdata_personvote
GROUP BY vote_event_id, option;

END;
