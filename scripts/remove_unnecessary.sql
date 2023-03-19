 delete from division where id not in (select division_id from post);
