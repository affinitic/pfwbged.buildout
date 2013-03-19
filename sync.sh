cd src
for pkg in collective.contact.core collective.contact.widget collective.dms.basecontent collective.dms.batchimport collective.dms.mailcontent collective.dms.thesaurus collective.task; do

    cd $pkg
    git remote add entrouvert git+ssh://git@repos.entrouvert.org/$pkg.git
    git pull; git pull entrouvert master; git push; git push entrouvert master
    cd -

done
