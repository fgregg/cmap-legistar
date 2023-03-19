SELECT 'drop table ' || t.name || ';' 
FROM sqlite_master t where type = 'table' and (name like 'pupa_%' OR name like 'django_%');
