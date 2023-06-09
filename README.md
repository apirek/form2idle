# Form2idle
Check if Formlabs Form 2 3D printer is idle.

## Description
### Check if printer is idle
```sh
./form2idle.py astutenewt.local
```
When the printer is idle the exit status will be 0.

### Print current time and remaining print time
Print the local time and the estimated remaining print time in hours, minutes, and seconds:
```sh
./form2idle.py -v astutenewt.local
2023-06-09 12:00:31, 1:37:02
```

or as estimated time of arrival:
```sh
./form2idle.py -v -e astutenewt.local
2023-06-09 12:00:31, 2023-06-09 13:37:33
```

### Wait for print to finish
Don't exit while the printer is busy:
```sh
./form2idle.py -w astutenewt.local
```
When the printer is idle the exit status will be 0.
