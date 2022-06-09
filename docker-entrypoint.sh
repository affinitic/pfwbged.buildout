#!/bin/bash
set -e

# ZConfig 2.9.1 is too old to do environment variable substitution on its own.
sed -i "s/\$(HOSTNAME)/$HOSTNAME/g" /plone/parts/instance/etc/zope.conf
sed -i "s/\$(HOSTNAME)/$HOSTNAME/g" /plone/parts/worker/etc/zope.conf

COMMANDS="adduser debug fg foreground help kill logreopen logtail reopen_transcript run show status stop wait"
START="console start restart"

# zeo
if [[ "$1" == "zeo"* ]]; then
  exec bin/$1 fg
fi

# worker
if [[ "$1" == "worker"* ]]; then
  exec bin/$1 fg
fi

# solr-instance
if [[ "$1" == "solr-instance"* ]]; then
  exec bin/$1 fg
fi

# Plone instance start
if [[ $START == *"$1"* ]]; then
  exec bin/instance console
fi

# Plone instance helpers
if [[ $COMMANDS == *"$1"* ]]; then
  exec bin/instance "$@"
fi

# Custom
exec "$@"
