#!/bin/bash

cd ../WoB_Server_ATNEngine
java -cp 'build/libs/WoB_Server_ATNEngine.jar:lib/*:chartlib/*' atn.ATNEngineBatchRunner $1 ../atn-data/$2
