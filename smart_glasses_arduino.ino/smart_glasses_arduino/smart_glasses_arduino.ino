// Smart Glasses Arduino - OPTIMIZED for Python Integration
// Fixed: Removed blocking delays, added non-blocking timing

const int TRIG_PIN = 10;        // Ultrasonic Trigger
const int ECHO_PIN = 11;        // Ultrasonic Echo  
const int VIBRATION_PIN = 6;    // Vibration motor

// Distance thresholds (in centimeters)
const int CRITICAL_DISTANCE = 20;
const int DANGER_DISTANCE = 40;
const int WARNING_DISTANCE = 70;
const int INFO_DISTANCE = 120;

// Timing variables for non-blocking operation
unsigned long lastDistanceCheck = 0;
unsigned long lastVibrationUpdate = 0;
unsigned long vibrationStartTime = 0;

const int DISTANCE_CHECK_INTERVAL = 100;  // Check distance every 100ms

// Vibration state
bool isVibrating = false;
int vibrationPattern = 0;  // 0=none, 1=warning, 2=danger, 3=critical
int vibrationCount = 0;
int vibrationMaxCount = 0;
unsigned long vibrationOnTime = 0;
unsigned long vibrationOffTime = 0;

// Last alert sent to prevent spam
String lastAlert = "";
unsigned long lastAlertTime = 0;

void setup() {
  // Initialize pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(VIBRATION_PIN, OUTPUT);
  
  // Initialize serial
  Serial.begin(9600);
  
  // Wait for serial connection (with timeout)
  unsigned long startTime = millis();
  while (!Serial && (millis() - startTime < 3000)) {
    delay(10);
  }
  
  // Startup vibration sequence
  digitalWrite(VIBRATION_PIN, HIGH);
  delay(200);
  digitalWrite(VIBRATION_PIN, LOW);
  delay(100);
  digitalWrite(VIBRATION_PIN, HIGH);
  delay(200);
  digitalWrite(VIBRATION_PIN, LOW);
  
  // Send ready signal
  Serial.println("ARDUINO_READY");
  Serial.println("SMART_GLASSES: System Ready");
  Serial.println("DISTANCE_SENSOR: Active");
  
  delay(500);  // Brief delay after startup
}

void loop() {
  unsigned long currentTime = millis();
  
  // Check distance at regular intervals (non-blocking)
  if (currentTime - lastDistanceCheck >= DISTANCE_CHECK_INTERVAL) {
    lastDistanceCheck = currentTime;
    
    int distance = getDistance();
    
    // Always send distance to Python
    Serial.print("DISTANCE:");
    Serial.println(distance);
    
    // Determine and send alerts based on distance
    if (distance > 0 && distance < CRITICAL_DISTANCE) {
      sendAlertOnce("ALERT:CRITICAL_DANGER", currentTime, 1000);
      startVibration(3);  // Critical pattern
    } 
    else if (distance >= CRITICAL_DISTANCE && distance < DANGER_DISTANCE) {
      sendAlertOnce("ALERT:DANGER_CLOSE", currentTime, 600);
      startVibration(2);  // Danger pattern
    }
    else if (distance >= DANGER_DISTANCE && distance < WARNING_DISTANCE) {
      sendAlertOnce("ALERT:WARNING_NEARBY", currentTime, 400);
      startVibration(1);  // Warning pattern
    }
    else if (distance >= WARNING_DISTANCE && distance < INFO_DISTANCE) {
      sendAlertOnce("INFO:OBJECT_AHEAD", currentTime, 300);
      stopVibration();
    }
    else {
      stopVibration();
    }
  }
  
  // Handle vibration patterns (non-blocking)
  updateVibration();
  
  // No delay here - loop runs as fast as possible!
}

int getDistance() {
  // Send ultrasonic pulse
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // Read echo with timeout
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  
  // Calculate distance in centimeters
  int distance = duration * 0.034 / 2;
  
  // Validate reading
  if (distance <= 0 || distance > 400 || duration == 0) {
    return -1;
  }
  
  return distance;
}

void sendAlertOnce(String alert, unsigned long currentTime, int minInterval) {
  // Only send alert if it's different or enough time has passed
  if (alert != lastAlert || (currentTime - lastAlertTime >= minInterval)) {
    Serial.println(alert);
    lastAlert = alert;
    lastAlertTime = currentTime;
  }
}

void startVibration(int pattern) {
  // Only restart if pattern changed
  if (vibrationPattern != pattern) {
    vibrationPattern = pattern;
    vibrationCount = 0;
    isVibrating = false;
    
    // Set pattern parameters
    switch (pattern) {
      case 1:  // Warning: single long pulse
        vibrationMaxCount = 1;
        vibrationOnTime = 400;
        vibrationOffTime = 0;
        break;
      case 2:  // Danger: two pulses
        vibrationMaxCount = 2;
        vibrationOnTime = 200;
        vibrationOffTime = 150;
        break;
      case 3:  // Critical: four rapid pulses
        vibrationMaxCount = 4;
        vibrationOnTime = 100;
        vibrationOffTime = 80;
        break;
      default:
        vibrationMaxCount = 0;
        break;
    }
  }
}

void stopVibration() {
  vibrationPattern = 0;
  vibrationCount = 0;
  isVibrating = false;
  digitalWrite(VIBRATION_PIN, LOW);
}

void updateVibration() {
  if (vibrationPattern == 0 || vibrationMaxCount == 0) {
    return;
  }
  
  unsigned long currentTime = millis();
  
  if (!isVibrating) {
    // Start new vibration pulse
    if (vibrationCount < vibrationMaxCount) {
      digitalWrite(VIBRATION_PIN, HIGH);
      isVibrating = true;
      vibrationStartTime = currentTime;
      vibrationCount++;
    } else {
      // Pattern complete, reset for next cycle
      vibrationCount = 0;
    }
  } else {
    // Check if vibration pulse should end
    if (currentTime - vibrationStartTime >= vibrationOnTime) {
      digitalWrite(VIBRATION_PIN, LOW);
      isVibrating = false;
      vibrationStartTime = currentTime;
    }
  }
  
  // Handle off time between pulses
  if (!isVibrating && vibrationCount > 0 && vibrationCount < vibrationMaxCount) {
    if (currentTime - vibrationStartTime >= vibrationOffTime) {
      // Ready for next pulse
      vibrationStartTime = currentTime;
    }
  }
}