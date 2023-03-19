SELECT 'alter table ' || t.name || ' rename to ' || substr(t.name, 15) || ';' 
FROM sqlite_master t where type = 'table' and name like 'opencivicdata_%';
