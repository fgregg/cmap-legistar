 delete from opencivicdata_division where id not in (select division_id from opencivicdata_post);
