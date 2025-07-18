import matplotlib.pyplot as plt
import csv

n = []
temp = []
humi = []

with open('sensordata.txt','r') as csvfile:
    _________________________________________ #read data from file
    for row in data:
        n.append(int(row[0]))
        temp.append(int(row[1]))
        humi.append(int(row[2]))

plt.plot(n, temp, label='temperature')
___________________________________ #plot humidity vs n
plt.xlabel('last 10 samples, 2 sec intervals')
plt.ylabel('temperature in deg C & humidity in %')
plt.title('Sensor data from AM2302')
plt.legend()
plt.show()
                 
  
