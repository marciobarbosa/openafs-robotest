
*** Settings ***
Documentation  Verify this test system is ready for the smoke test.
Library        OperatingSystem

*** Test Cases ***
Filesystem is not mounted
    ${mount}=             Run           mount
    Should not contain    ${mount}      AFS on /afs

Kernel module is not loaded
    ${modules}=           Get file      /proc/modules
    Should not contain    ${modules}    openafs
    Should not contain    ${modules}    libafs

Installation directories are not present
    Directory should not exist    /afs
    Directory should not exist    /usr/afs
    Directory should not exist    /usr/vice/etc

System configuration file is not present
    File should not exist         /etc/sysconfig/openafs

Server partition is present
    Directory should exist        /vicepa
    # The following check is not needed if /vicepa is a real partition.
    File should exist             /vicepa/AlwaysAttach

Server partition is empty
    Directory should not exist    /vicepa/AFSIDat

Test keytabs are available
    File should exist    ${KRB_USER_KEYTAB}
    File should exist    ${KRB_AFS_KEYTAB}

Able to create a test user ticket
    No ticket
    Create ticket
    Have ticket
    Destroy ticket
    No ticket

*** Keywords ***
No ticket
    ${rc}    ${output}    Run and return rc and output    klist
    Log      ${output}
    Should be equal as integers    ${rc}    1

Have ticket
    ${rc}    ${output}    Run and return rc and output    klist
    Log      ${output}
    Should be equal as integers    ${rc}    0

Create ticket
    ${rc}    ${output}    Run and return rc and output    kinit -k -t ${KRB_USER_KEYTAB} ${AFS_TESTUSER}@${KRB_REALM}
    Log      ${output}
    Should be equal as integers    ${rc}    0

Destroy ticket
    ${rc}    ${output}    Run and return rc and output    kdestroy
    Log      ${output}
    Should be equal as integers    ${rc}    0
