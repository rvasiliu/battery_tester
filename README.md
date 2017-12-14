# Mon Django Starter

A git repo with the initial boilerplate for a django project used by
the monitoring team.

Has initial points for for a clean django and webpack config.

## Prerequisites:
You need to have the following:

* [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/)
* [postgres](https://tecadmin.net/install-postgresql-server-on-ubuntu/#)
* [nodejs/npm](https://www.digitalocean.com/community/tutorials/how-to-install-node-js-on-an-ubuntu-14-04-server)
* [nvm](https://github.com/creationix/nvm)

Be sure you have the latest npm (something above `4.0`):
```bash
$ npm install -g npm
```

You'll also need webpack and webpack-dev-server globally:
```bash
$ npm install -g webpack
$ npm install -g webpack-dev-server
```

I you managed to get a project like `glue` running,
you're probably all set.
If `zenoss_palantir` or `capman` work for you, then you'll probably only
need the nodejs/npm/nvm stuff.

## Usage
To use the build script, first add an alias in `~/.bash_aliases` (or`.bashrc`):
```bash
_init_django_project(){
  curl --user <your_github_username>  \
  --header 'Accept: application/vnd.github.v3.raw' \
  --location https://api.github.com/repos/cegeka/mon_django_starter/contents/init_project.sh > init_project.sh;
 bash init_project.sh $@
 rm init_project.sh
}
alias init_django_project=_init_django_project
```

Reload:
```
$ source ~/.bashrc
```

Now you can use the command:
```
$ init_django_project untitled
```

Now the script will be downloaded locally.
It will start installing everything for pip and node.
After some time (5-10 minutes, downloading all the dependencies is slow)
you will be asked for 3 things:
 * database name
 * database user
 * password for the LDAP server (a pim link is provided in the script)


For people that use shared folders, npm needs to be used with `no-bin-links`.
The script passes the second argument to npm install, so this will work:
```
$ init_django_project untitled --no-bin-links
```

## Running project in development

Running in development implies running two test servers (in separate terminals):
```bash
$ python manage.py runserver
$ npm run watch-dev-server
```

This configuration can be used locally. The webpack dev server will generate
 assets locally. 
 
<div style="background-color: #ffcfa0">
 You need to run npm run build before committing a production
 build.
</div>
 

