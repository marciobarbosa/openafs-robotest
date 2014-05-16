*** Setting ***
Library        OperatingSystem
Library        libraries/Kerberos.py
Resource       keywords/utility.robot

*** Keywords ***
afs service key should exist
    file should exist    /usr/afs/etc/rxkad.keytab

afs service key should not exist
    file should not exist    /usr/afs/etc/rxkad.keytab

import afs service key
    sudo    cp ${KRB_AFS_KEYTAB} /usr/afs/etc/rxkad.keytab
