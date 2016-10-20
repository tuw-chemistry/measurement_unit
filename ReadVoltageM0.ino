/*
  ReadAnalogVoltage
  Reads an analog input on pin 0, converts it to voltage, and prints the result to the serial monitor.


 This example code is in the public domain.
 */

// the setup routine runs once when you press reset:
void setup() {
  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);
}

// the loop routine runs over and over again forever:
void loop() {
  //set the analogReadResolution to 12 bits
  analogReadResolution(12);
  // read the input on analog pin 0:
  int sensorValue = analogRead(A0);
  // Convert the analog reading (which goes from 0 - 4095) to a voltage (0 - 3.3V):
  float voltage = sensorValue * (3300.0 / 4095.0); //in milivolts
  // print out the value you read:
  SerialUSB.println(voltage);
  delay(500);
}
