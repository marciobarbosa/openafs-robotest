# Copyright (c) 2015 Sine Nomine Associates
# Copyright (c) 2001 Kungliga Tekniska Högskolan
# See LICENSE

*** Settings ***
Documentation     Volserver/vlserver tests
Resource          common.robot
Suite Setup       Login  ${AFS_ADMIN}
Suite Teardown    Logout

*** Variables ***
${SERVER}      ${FILESERVER}
${VOLID}       0

*** Test Cases ***
Create a Volume
    [Teardown]  Remove Volume  xyzzy
    Volume Should Not Exist  xyzzy
    Command Should Succeed   ${VOS} create ${SERVER} a xyzzy
    Volume Should Exist      xyzzy
    Volume Location Matches  xyzzy  server=${SERVER}  part=a

Move a Volume
    [Setup]     Create Volume  xyzzy
    [Teardown]  Remove Volume  xyzzy
    Command Should Succeed   ${VOS} move xyzzy ${SERVER} a ${SERVER} b
    Volume Should Exist      xyzzy
    Volume Location Matches  xyzzy  server=${SERVER}  part=b

Add a Replication Site
    [Setup]     Create Volume  xyzzy
    [Teardown]  Remove Volume  xyzzy
    Command Should Succeed    ${VOS} addsite ${SERVER} a xyzzy
    Command Should Succeed    ${VOS} remsite ${SERVER} a xyzzy

Release a Volume
    [Setup]     Create Volume  xyzzy
    [Teardown]  Remove Volume  xyzzy
    Command Should Succeed    ${VOS} addsite ${SERVER} a xyzzy
    Command Should Succeed    ${VOS} release xyzzy
    Volume Should Exist       xyzzy.readonly
    Volume Location Matches   xyzzy  server=${SERVER}  part=a  vtype=ro

Remove a Replication Site
    [Setup]     Create Volume  xyzzy
    [Teardown]  Run Keywords   Command Should Succeed  ${VOS} remove ${SERVER} a xyzzy.readonly
    ...         AND            Remove Volume  xyzzy
    Command Should Succeed    ${VOS} addsite ${SERVER} a xyzzy
    Command Should Succeed    ${VOS} release xyzzy
    Command Should Succeed    ${VOS} remsite ${SERVER} a xyzzy
    Volume Should Exist       xyzzy.readonly

Remove a Replicated Volume
    [Setup]     Create Volume   xyzzy
    [Teardown]  Remove Volume   xyzzy
    Command Should Succeed    ${VOS} addsite ${SERVER} a xyzzy
    Command Should Succeed    ${VOS} release xyzzy
    Command Should Succeed    ${VOS} remove ${SERVER} a -id xyzzy.readonly
    Command Should Succeed    ${VOS} remove -id xyzzy
    Volume Should Not Exist   xyzzy.readonly
    Volume Should Not Exist   xyzzy

Create a Backup Volume
    [Setup]     Create Volume   xyzzy
    [Teardown]  Remove Volume   xyzzy
    ${output}=  Run           ${VOS} backup xyzzy
    Should Contain            ${output}  xyzzy

Display Volume Header Information
    [Setup]     Create Volume   xyzzy
    [Teardown]  Remove Volume   xyzzy
    ${output}=  Run           ${VOS} listvol ${SERVER} a
    Should Contain            ${output}  xyzzy

Display VLDB Information
    [Setup]     Create Volume   xyzzy
    [Teardown]  Remove Volume   xyzzy
    ${output}=  Run             ${VOS} listvldb -server ${SERVER}
    Should Contain              ${output}  xyzzy

Display Header and VLDB Information
    [Setup]     Create Volume   xyzzy
    [Teardown]  Remove Volume   xyzzy
    ${output}=  Run             ${VOS} examine xyzzy
    Should Contain              ${output}  xyzzy

Avoid creating a rogue volume during create
    [Tags]         rogue-avoidance
    [Teardown]     Cleanup Rogue    ${vid}
    Set test variable    ${vid}    0
    ${vid}=        Create volume    xyzzy    ${SERVER}    a    orphan=True
    Command Should Fail    ${VOS} create -server ${SERVER} -part b -name xyzzy -id ${vid}

*** Keywords ***
Cleanup Rogue
    [Arguments]     ${vid}
    Remove volume   ${vid}    server=${SERVER}
    Remove volume   ${vid}    server=${SERVER}    zap=True
