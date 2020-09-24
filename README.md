# nexus-migration
Python script to migrate assets from Sonatype Nexus v2 to v3

### Usage

nexus-migration.py [-h] [-t TOKEN] [-d DESTINATION] repo type

Nexus repository migration through assets API

#### positional arguments:

  repo                  name of the origin repo
  type                  type of repo (maven2, npm)

#### optional arguments:

  -h, --help            							   show this help message and exit

  -t, --token TOKEN    						continuation token from asset list

  -d, --destination DESTINATION	 destination repo (if it has a different name than origin)