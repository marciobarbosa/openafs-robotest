# Copyright (c) 2015 Sine Nomine Associates
# Copyright (c) 2001 Kungliga Tekniska Högskolan
# See LICENSE

*** Settings ***
Resource          common.robot
Suite Setup       Login  ${AFS_ADMIN}
Suite Teardown    Logout

*** Variables ***
${SERVER}      ${FILESERVER}

*** Test Cases ***
Avoid creating a rogue volume during backup
    [Tags]         rogue-avoidance
    [Teardown]     Run Keywords    Remove volume    xyzzz
    ...            AND             Cleanup Rogue    ${vid_bk}
    Set test variable    ${vid}    0
    Command Should Succeed    ${VOS} create ${SERVER} a xyzzy
    Command Should Succeed    ${VOS} remove ${SERVER} a -id xyzzy
    ${vid_bk}=        Create volume    xyzzy    ${SERVER}    b    orphan=True
    ${vid}=           Evaluate    ${vid_bk} - 2
    Command Should Succeed    ${VOS} create ${SERVER} a xyzzz -id ${vid} 
    Command Should Fail       ${VOS} backup xyzzz

*** Keywords ***
Cleanup Rogue
    [Arguments]     ${vid}
    Remove volume   ${vid}    server=${SERVER}
    Remove volume   ${vid}    server=${SERVER}    zap=True
