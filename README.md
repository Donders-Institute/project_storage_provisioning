# Project Provisioning System: a tool for managing the ACL of project storage

## Requirements
- Python 2.7+
- Environment modules

## Configuration
The configuration file is located in the `etc` directory.  It should be changed by administrator.

## Usage for end-users
The end-user scripts are right in the top-level directory of the code.  They are:

- `getacl.py` is used for retrieving current user roles associated with project(s).
- `setacl.py` is used for setting or altering user roles associated with project(s).  Only project administrator can do it.
- `delacl.py` is used for deleting a user's role from a project.  Only project administrator can do it.

Those scripts require certain environment variables to be set and it also requires python 2.7.  Assuming an user in the
HPC cluster at DCCN, (s)he can use the following commands to run `getacl.py` for a project with ID `3010000.01`:

```Bash
$ module load python/2.7.8
$ getacl.py 3010000.01
```

Each script has few command-line options, one can use `-h` option to show details of the usage.  

## Notes on cron scripts
The scripts in the `cron` directory has hard-coded path which requires to be adjusted before using them.  It also assumes
the usage of [Environment Modules](http://modules.sourceforge.net/) for setting up required environmental variables.