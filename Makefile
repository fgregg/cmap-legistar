export DJANGO_SETTINGS_MODULE=pupa.settings

cmap.db :
	DATABASE_URL=sqlite:///`pwd`/$@ pupa dbinit us
	DATABASE_URL=sqlite:///`pwd`/$@ pupa update cmap --fastmode
	cat scripts/vote_counts.sql | sqlite3 $@
	cat scripts/drop.sql | sqlite3 $@ | sqlite3 $@
	cat scripts/remove_unnecessary.sql | sqlite3 $@
	echo "vacuum;" | sqlite3 $@
