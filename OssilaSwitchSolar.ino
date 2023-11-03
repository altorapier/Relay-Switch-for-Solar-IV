int x;
int p;
int pins[8] = {3,4,5,6,7,8,9,10};

void setup() 
{
  int w;
  for(w=0; w<8;w++)
  {
    pinMode(pins[w],OUTPUT);
    digitalWrite(pins[w], HIGH);
  }
  pinMode(11,OUTPUT);
  digitalWrite(11,HIGH);
  Serial.begin(9600);
}

void loop() 
{
  while (Serial.available() >= 2)
  {
    p = Serial.read()+1;
    x = Serial.read();
    if (p > 0 && p< 10)
    {
      if (x == 0)
      {
        digitalWrite(pins[p-1], HIGH);
      }
      if (x == 1)
      {
        digitalWrite(pins[p-1], LOW);
      }
    }
    if (p == 20)
    {
      if (x == 0)
      {
        digitalWrite(11,HIGH);
      }
      if (x == 1)
      {
        digitalWrite(11,LOW);
      }
    }
  }

}
