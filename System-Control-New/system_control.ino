#include helpers.hpp
#include config.h

#define CURRENT_LOGGING X

#if CURRENT_LOGGING = X
  #define MOTOR_R PIN
  #define MOTOR_L PIN
  #define ARM_ACT PIN
  #define BUCKET_ACT PIN
#endif

//Catagories
  //----------------------------------------------------------------------------------
  //                             Arm Actuators Setup
  //----------------------------------------------------------------------------------
//Define actuator and actuator potentiometer pins
#if PCB_BOARD_SCHEMATIC = BERM
  //Arm Actuator Pins
  #define PIN for left = X
  #define PIN for right = X
#endif

#if PCB_BOARD_SCHEMATIC = BERM
  //Potentiometer Pins
  #define potentiometer PIN for right = X
  #define potentiometer PIN for left = X
#endif

#if MAIN_ROBOT = BERM
  #if PCB_BOARD_SCHEMATIC = BERM
    //Define Limits for arm actuators potentiometers and stroke length
    #define actuator potenti MAX = X
    #define actuator potenti MIN = X
    #define actuator stroke = X
  #endif
#endif

#if MAIN_ROBOT = BERM
  //Soft; sends LED flashing yellow and restricts movement
  float mins = X
  float maxes = X
  //Hard; shuts down system and flashes red LED; for LED's just use these floats in saftey code.
  float mins = X
  float maxes = X
  //velocities for arm actuators
  float min = X
  float max = X
#endif

//Sets PID variables and PWM drivers
#if ARM_ACTUATORS_ENABLED
  PID pidL(2.2, 0.0022, 0.34, 2.0);
  PID pidR(1.85, 0.0018, 0.31, 1.7);

  PWM_Driver left_driver(DRV12_PWM_PIN, DRV12_DIR1_PIN, DRV12_DIR2_PIN, false);
  Actuator act_left(left_driver, pidL, POTL_PIN, AL_POT_MIN, AL_POT_MAX, ALR_STROKE, act_max_vel,20,150);
  PWM_Driver right_driver(DRV11_PWM_PIN, DRV11_DIR1_PIN, DRV11_DIR2_PIN, false);
  Actuator act_right(right_driver, pidR, POTR_PIN, AR_POT_MIN, AR_POT_MAX, ALR_STROKE, act_max_vel,20,150);
#endif

  //----------------------------------------------------------------------------------
  //                           Bucket Actuators Setup
  //----------------------------------------------------------------------------------
//Define actuator and actuator potentiometer pins
#if PCB_BOARD_SCHEMATIC = BERM
  //Bucket Actuator Pin
  #define PIN for bucket = X
#endif

#if PCB_BOARD_SCHEMATIC = BERM
  //Potentiometer Pins
  #define potentiometer PIN for bucket = X
#endif

#if ARM_ACTUATORS_ENABLED==1 && BUCKET_ACTUATOR_ENABLED==1 && MAIN_ROBOT==1
  #define BUCKET_END_CORRECTION 1 
  #define BUCKET_AUTO_CORRECTION 1
#endif

#if MAIN_ROBOT = BERM
  //Soft; sends LED flashing yellow and restricts movement
  float bucket soft mins = X
  float bucket soft maxes = X
  //Hard; shuts down system and flashes red LED; for LED's just use these floats in saftey code.
  float bucket hard mins = X
  float bucket hard maxes = X
#endif

#if BUCKET_ACTUATOR_ENABLED
  PID pidB(3.0, 0.001, 0.4);

  PWM_Driver bucket_driver(DRV21_PWM_PIN, DRV21_DIR1_PIN, DRV21_DIR2_PIN, true);
  Actuator act_bucket(bucket_driver, pidB, POTB_PIN, AB_POT_MIN, AB_POT_MAX, AB_STROKE, act_max_vel, bucket_min, bucket_max);
#endif
  //----------------------------------------------------------------------------------
  //                             Drive Motor Setup
  //----------------------------------------------------------------------------------
#if MAIN_ROBOT = BERM
  //Define motor pins
  const int LEFT_MOTOR_PIN = X
  const int RIGHT_MOTOR_PIN = X
  const int COMMON_PIN = X
#endif

int max_motor_vel = X
int motor_right_speed = 0
int motor_left_speed = 0
int motor_leftright_rotation = 0
int motor_leftright_arc_radius = 0
float robot_width = X
float bucket_dynamic_max=arm_soft_max

#if MAIN_ROBOT==0
  #define motor_left_speed_scale = 1
  #define motor_right_speed_scale = 1
#endif

// Initalize motor classes
#if MOTORS_ENABLED
  // Set up motors
  #if MAIN_ROBOT==0 || MAIN_ROBOT==1
    OutPin motor_left_dac1(DACL1_PIN);
    OutPin motor_left_dac2(DACL2_PIN);
    OutPin motor_right_dac1(DACR1_PIN);
    OutPin motor_right_dac2(DACR2_PIN);
    OutPin motor_enable(EN_PIN);
    Motor motor_left(motor_left_dac1, motor_left_dac2, motor_enable, motor_max_vel, false);
    Motor motor_right(motor_right_dac1, motor_right_dac2, motor_enable, motor_max_vel, true);
  #else
    SimpleMotor simpleMotorRight(3, 4, 9, motor_max_vel);
    SimpleMotor simpleMotorLeft(6, 7, 8, motor_max_vel);
  #endif
#endif
  //----------------------------------------------------------------------------------
  //                               LIDAR Setup
  //----------------------------------------------------------------------------------

//Will look into this later

  //----------------------------------------------------------------------------------
  //                        LED System, IBUS and IMU Setup
  //----------------------------------------------------------------------------------

#if IBUS_RECIVER_ENABLED
  IBusReader ibus(Serial1);
#endif

// LED Pins
#define LEDR_PIN X
#define LEDY_PIN X
#define LEDG_PIN X
// LED Saved states
short int led_r = 0;
short int led_y = 0;
short int led_g = 0;
// Led error states
enum LedState { OFF = 0, NONE = -1, ON = 1, BLINK = 2 };
//LED class set-up
#if ERROR_LEDS_ENABLED
  OutPin ledr_pin(LEDR_PIN);
  OutPin ledy_pin(LEDY_PIN);
  OutPin ledg_pin(LEDG_PIN);
  OutPin ledb_pin(LEDB_PIN);
#endif

// IMU sensor setup
#if IMU_SENSOR_ENABLED
  #if MAIN_ROBOT==2
    #define IMU_MANUAL_SCALER 1
  #else
    #define IMU_MANUAL_SCALER 0.6
  #endif
  MPU6050 IMU; 

  #define IMU_offset_bias_samples 25
  #define IMU_filter_constant 0.2
  float IMU_offset_bias=0;
  float IMU_rate = 0;
  float IMU_yaw=0;
  unsigned long last_IMU_time =0;
  float IMU_raw_home_bias = 0;
  float IMU_local_home_bias = 0;
  bool reset_IMU_local_home=false;
  bool update_IMU_raw_home=true;
  float IMU_filter_rate=0;

  #define IMU_angle_bias_samples 25
  float IMU_yaw_scale=0;
#endif

  //----------------------------------------------------------------------------------
  //                             System Variables
  //----------------------------------------------------------------------------------
//Timing variables
//Motor and actuator timeout variables (probably put these in their sections)
//Serial and state
//PID controller velo gain
// Timing
int update_rate = 200;                // hz
int update_actuator_feedback = 1000;  // hz
int feedback_rate = 10;               // hz
int reset_int_rate = 10;              // hz
unsigned long last_update_time = 0;
unsigned long last_update_actuator_time = 0;
unsigned long last_feedback_time = 0;
unsigned long last_reset_int_time = 0;
unsigned long led_blink_time=0;
unsigned long current_time = 0;
const unsigned long estop_timeout = 2000;  // 2 second timeout for failed serial commication
unsigned long last_message_time = 0;
unsigned long last_error_message_time = 0;  
int error_message_interval = 2000;
bool emergency_stop = false;
String system_fault_msg = "";
bool system_started = false;
//int rc_startup_state=0;
#if CURRENT_LOGGING==1
  unsigned long last_amp_time = 0;
  const int amp_update_rate = 20; // hz
  float amp_average_left_motor = 0;
  float amp_average_right_motor = 0;
  float amp_average_arm_actuators = 0;
  float amp_average_bucket_actuators = 0;
  int amp_tick_count = 0;
#endif

#if SENSOR_OUTPUT == 7
  unsigned long last_report_time = 0;
  int count_A = 0;
  int count_M = 0;
  int count_A_zero = 0;
  int count_A_nonzero = 0;
  int count_M_zero = 0;
  int count_M_nonzero = 0;
#endif

// Motor and actuator timeout variables, shutdown motors and actuators if a message is not reviced within timeout period
unsigned long last_actuator_cmd_time = 0; 
unsigned long last_motor_cmd_time = 0;
int motor_timeout = 300;
int actuator_timeout = 300;

// Serial and state
bool serial_connection_established=false;
bool RC_connection_established=false;
bool receiving_message = false;
bool at_bucket_min = false;
bool at_bucket_max = false;
bool dual_actuator_correct = false;
int serial_index = 0;
int expected_length = -1;
bool control_take_over=false;
const int MY_SERIAL_BUFFER_SIZE = 128;
byte serial_buffer[MY_SERIAL_BUFFER_SIZE];

// Set up PID controllers velocity gain
float vel_gain = 2.5;
  //----------------------------------------------------------------------------------
  //                            Subsystem Classes Setup
  //----------------------------------------------------------------------------------
// Did it in the main actuators and motors channels, felt more readable if it was just commented as a class
void sendSerialFeedback(char command, uint8_t* data, size_t dataLen);
//The void setup just start all components
void setup(){
  delay(5);
  Serial.begin(115200);
}
//Void loop should be split into several different parts similar to how the catagories are set up
//All saftey in one spot, all data updates in one spot, and all autonomy in one spot.
void loop(){

//Set speeds for motors
//Set ramping acceleration and velocity to reach max speeds (old code doesn't have this)
//Have PID loops to make sure motors are consistent and don't double inout etc
//Have timeouts and saftey features (research into more features)
//Implement new serial protocol into giving motor velocity and status back to the Jet
  
  #if IBUS_RECIVER_ENABLED
  // Read serial and process messages while being Non-blocking
    if (ibus.update()) {
      #if SENSOR_OUTPUT == 3
        int16_t* joy = ibus.getJoystick(true);
        Serial.print("Raw RC controller inputs: ");
        for (int i = 0; i < 12; i++) {  
          Serial.print(joy[i]);
          Serial.print(" ");
        }
        Serial.println("");
      #elif SENSOR_OUTPUT == 2
        int16_t* joy = ibus.getJoystick();
        Serial.print("RC controller inputs: ");
        for (int i = 0; i < 6; i++) {  
          Serial.print(joy[i]);
          Serial.print(" ");
        }
        Serial.println("");
      #else
        int16_t* joy = ibus.getJoystick();
        // if(joy[4]==0) rc_startup_state=1;
        // else if(joy[4]==1 && rc_startup_state==1) rc_startup_state=2;
        // else if(joy[4]==0 && rc_startup_state==2) rc_startup_state=1;
        // && rc_startup_state==2
        if(joy[4]==0) {
          mL_speed=0;
          mR_speed=0;
          aL_speed=0;
          aR_speed=0;
          aB_speed=0;
          control_take_over=true;
        }
        // && rc_startup_state!=0
        else {
          #if MAIN_ROBOT==1
            int16_t steering = joy[2];
            int16_t throttle = joy[3]; 
            mR_speed = constrain(throttle - steering, -30, 30);
            mL_speed = constrain(throttle + steering, -30, 30);
            aLR_tgt = -1;
            aB_tgt = -1;
            aB_speed = -joy[0];
            aL_speed = joy[1];
            aR_speed = aL_speed;
            last_actuator_cmd_time=current_time;
            last_motor_cmd_time=current_time;
          #else
            int16_t steering = joy[2];
            int16_t throttle = joy[3]; 
            mR_speed = constrain(throttle - steering, -30, 30);
            mL_speed = constrain(throttle + steering, -30, 30);
            aLR_tgt = -1;
            aB_tgt = -1;
            aB_speed = joy[0];
            aL_speed = joy[1];
            aR_speed = aL_speed;
          #endif
          #if SENSOR_OUTPUT == 4
            uint8_t motorACTvalues[16]
            memcpy(motorACTvalues,     &mL_speed, 4);
            memcpy(motorACTvalues + 4, &mR_speed, 4);
            memcpy(motorACTvalues + 8, &aR_speed, 4);
            memcpy(motorACTvalues + 12, &aB_speed, 4);
            sendSerialFeedback('M', averageampsData, 16);
          #endif
          if(RC_connection_established==false){
            RC_connection_established=true;
            systemFault(false,"","", NONE, NONE, ON);
          }
        }
      #endif
    } 
    else{
      control_take_over=false;
      if(serial_connection_established==false) {
        #if SERIAL_COMM_TIMEOUT_FAULT
          systemFault(true,"Serial communication timeout.","", NONE, NONE, BLINK);
        #else 
          systemFault(false,"Serial communication timeout.","", NONE, NONE, BLINK);
        #endif
      }
    }
    
    
  #endif

//Arm and Bucket actuator updators with new feedback code
  if (current_time - last_update_actuator_time >= 1000 / update_actuator_feedback) {
    last_update_actuator_time = current_time;
    #if SENSOR_OUTPUT == 5
      Serial.print("Act pos: ");
    #endif
    #if ARM_ACTUATORS_ENABLED
      aL_pos = act_left.update_pos("Act L: ");
      aR_pos = act_right.update_pos("Act R: ");
      #if SENSOR_OUTPUT == 5
          //Serial Feedback Command For Arm Actuator Positions
          uint8_t LRpositionData[8];
          memcpy(LRpositionData,     &aL_pos, 4);
          memcpy(LRpositionData + 4, &aR_pos, 4);
          sendSerialFeedback('P', LRpositionData, 8);
      #endif
    #endif
    #if BUCKET_ACTUATOR_ENABLED
      aB_pos = act_bucket.update_pos("Act B: ");
      #if SENSOR_OUTPUT == 5
          //Serial feedback for bucket act @615
          uint8_t BucpositionData[4];
          memcpy(BucpositionData,     &aB_pos, 4);
          sendSerialFeedback('B', BUCpositionData, 4);   
      #endif
    #endif
    #if SENSOR_OUTPUT == 5
      Serial.println("");
    #endif
  }

//Current logging with new serial feedback starting @864
#if CURRENT_LOGGING==1
  if(current_time - last_amp_time >= 1000 / amp_update_rate){
    last_amp_time = current_time;
    amp_tick_count+=1;

    amp_average_left_motor+=analogRead(CURRENT_LEFT_MOTOR);
    amp_average_right_motor+=analogRead(CURRENT_RIGHT_MOTOR);
    amp_average_arm_actuators+=analogRead(CURRENT_ARM_ACTUATORS);
    amp_average_bucket_actuators+=analogRead(CURRENT_BUCKET_ACTUATORS);
    if(amp_tick_count>=20){
      amp_tick_count=0;

      amp_average_left_motor=abs(amp_average_left_motor/amp_update_rate);
      amp_average_left_motor=(amp_average_left_motor - 530.0) / 13.5;

      amp_average_right_motor=abs(amp_average_right_motor/amp_update_rate);
      amp_average_right_motor=(amp_average_right_motor - 460.0) / 13.5;

      amp_average_arm_actuators=abs(amp_average_arm_actuators/amp_update_rate);
      amp_average_arm_actuators=(amp_average_arm_actuators - 530.0) / 13.5;

      amp_average_bucket_actuators=abs(amp_average_bucket_actuators/amp_update_rate);
      amp_average_bucket_actuators=(amp_average_bucket_actuators - 530.0) / 13.5;

    if(amp_average_left_motor <= 0.25)
        amp_average_left_motor = 0.0;

    if(amp_average_right_motor <= 0.25)
        amp_average_right_motor = 0.0;

    if(amp_average_arm_actuators <= 0.25)
        amp_average_arm_actuators = 0.0;

    if(amp_average_bucket_actuators <= 0.25)
        amp_average_bucket_actuators = 0.0;
      
      //Feedback for currents 
      uint8_t averageampsData[16]
      memcpy(averageampsData,     &amp_average_left_motor, 4);
      memcpy(averageampsData + 4, &amp_average_right_motor, 4);
      memcpy(averageampsData + 8, &amp_average_arm_actuators, 4);
      memcpy(averageampsData + 12, &amp_average_bucket_actuators, 4);
      sendSerialFeedback('A', averageampsData, 16);
    
      amp_average_left_motor = 0;
      amp_average_right_motor = 0;
      amp_average_arm_actuators = 0;
      amp_average_bucket_actuators = 0;
      Serial.println("");
    }
  }
#endif
}

// Read serial communication from autonomy computer and set system variables to output.
void processMessage(byte *data, int length) {
  current_time = millis();
  char type = data[0];
  #if DEBUG_MODE
    Serial.print("Received message of type: ");
    Serial.println(type);
    Serial.print("Length: ");
    Serial.println(length);
  #endif
  bool cmd_triggered = true;
  switch (type) {
    // Chnage actuator speeds/positions
    case 'A':
      {      
        if(control_take_over) break;
        #if BUCKET_ACTUATOR_ENABLED || ARM_ACTUATOR_ENABLED       
          // (A, actuators) Recvived Arm and Bucket actuator speeds and positions.
          aLR_tgt = (int16_t)((data[1] << 8) | data[2]);  // Adjusted index to skip the type byte
          aB_tgt = (int16_t)((data[3] << 8) | data[4]);
          aL_speed = -(int8_t)data[5];
          aR_speed = aL_speed;
          aB_speed = -(int8_t)data[6];
          #if SENSOR_OUTPUT==7
            if (aL_speed == 0 && aB_speed == 0) count_A_zero++;
            else count_A_nonzero++;
          #endif
          #if DEBUG_MODE
            uint8_t armbuckposveloc[16]
            memcpy(armbuckposveloc,     &aLR_tgt, 4);
            memcpy(armbuckposveloc + 4, &aB_tgt, 4);
            memcpy(armbuckposveloc + 8, &aL_speed, 4);
            memcpy(armbuckposveloc + 12, &aB_speed, 4);
            sendSerialFeedback('V', armbuckposveloc, 16);
          #endif
          last_actuator_cmd_time=current_time;
        #endif
        break;
      }
    // Change motor speeds
    case 'M':
      {    
        if(control_take_over) break;
        #if MOTORS_ENABLED
          // (M, motors) Recvived left and right motor speeds
          mR_speed = (int8_t)data[1];  
          mL_speed = (int8_t)data[2];
          #if SENSOR_OUTPUT==7
            if (mR_speed == 0 && mL_speed == 0) count_M_zero++;
            else count_M_nonzero++;
          #endif
          #if DEBUG_MODE
            uint8_t motorautospeed[8]
            memcpy(motorautospeed,     &mL_speed, 4);
            memcpy(motorautospeed + 4, &mR_speed, 4);
            sendSerialFeedback('S', motorautospeed, 8);
          #endif
          last_motor_cmd_time=current_time;
        #endif
        break;
      }
    // Rotate robot
    case 'R': 
      { 
        #if IMU_SENSOR_ENABLED && MOTORS_ENABLED
        // (R, rotate) Recvives a rotation speed, angle, radius, and home reset, to allow arc or stationary turns       
        mLR_rotation_speed = (int8_t)data[1]; 
        if(mLR_rotation_speed>0&&mLR_rotation_speed>motor_max_vel) mLR_rotation_speed=motor_max_vel;
        else if(mLR_rotation_speed<0&&mLR_rotation_speed<-motor_max_vel) mLR_rotation_speed=-motor_max_vel;
        mLR_rotation = -(int8_t)data[2];
        mLR_arc_radius = (int8_t)data[3];
        reset_IMU_local_home = (int8_t)data[4];
        update_IMU_raw_home=false;
        if(mLR_arc_radius==0&&mLR_rotation_speed==0&&mLR_rotation==0&&reset_IMU_local_home==true) IMU_local_home_bias=IMU_yaw;
        #if DEBUG_MODE
          uint8_t motorrotationspeed[12]
          memcpy(motorrotationspeed,     &mLR_rotation_speed, 4);
          memcpy(motorrotationspeed + 4, &mLR_arc_radius, 4);
          memcpy(motorrotationspeed + 8, &mLR_rotation, 4);
          sendSerialFeedback('R', motorrotationspeed, 12);
        #endif
        last_motor_cmd_time=current_time;
        #endif
        break;
      }
    // Servo state
    case 'S':    
      { 
        #if SERVO_MOTOR_ENABLED
        servo.write(data[1]);
        #if SENSOR_OUTPUT == 8
          Serial.print("Servo State: ");
          Serial.println(data[1]);
        #endif
        #endif
        break;
      }
    // E-STOP REBOOT
    case 'B':
    // USE E-STOP RESETS WITH EXTREAM CAUTION, THIS CAN BE DANGRUS TO THE WHOLE ROBOT.
    // This command should only be sent by a user whom knows the dangers and system workings, so (no automated button) and (no autonomy resets) and if a controller is used the (reset should require a combanation of 3+ buttons to do the reset)
      { 
        emergency_stop=false;
        break;
      }
    /*case 'L':
      {                   
        //led_r = data[1];  
        //led_y = data[2];
        //led_g = data[3];
        //led_b = data[4];
        #if DEBUG_MODE
          Serial.print("Red: ");
          Serial.print(led_r);
          Serial.print(" Yellow: ");
          Serial.print(led_y);
          Serial.print(" Green: ");
          Serial.print(led_g);
          Serial.print(" Blue: ");
          Serial.println(led_b);
        #endif
        break;
      }*/
    // Send data infomation
    case 'D':
      // IDs: 0-32 are saved for 
      {
        // Save interger first byte as payload: (0-64) reserved for now, rest are used for data.
        int id=data[1];
        //char id[4];                         
        //sprintf(id, "%d", data[1]);  
        
        // Determine what to do with saved data
        int operation=data[2];
        //char operation[4];                         
        //sprintf(operation, "%d", data[2]); 
        
        // Get data payload and have messages calss handle all farther message handling
        uint8_t* payload = &data[3]; 
        #if SCREEN_ENABLED
          messages.addMessageToArduino(id, operation, payload);
        #endif
        break;
      }
    default:
      Serial.println("Unknown message type");
      cmd_triggered=false;
    break;
  }
  last_message_time=current_time;
  if(serial_connection_established==false && cmd_triggered==true){
    serial_connection_established=true;
    systemFault(false,"","", NONE, NONE, ON);
  }
}

// This logs the IMU sensor over a number of sample to get an mean value, and then uses some math to figure out the angle of the IMU sensor
void calibrateIMUAngle() {
  // Record accelerometer and find average acceloration in each direction
  int16_t ax, ay, az;
  long ax_sum = 0, ay_sum = 0, az_sum = 0;
  for (int i = 0; i < IMU_angle_bias_samples; i++) {
      IMU.getAcceleration(&ax, &ay, &az);
      ax_sum += ax;
      ay_sum += ay;
      az_sum += az;
      delay(10);
  }
  float ax_avg = (float)ax_sum / IMU_angle_bias_samples;
  float ay_avg = (float)ay_sum / IMU_angle_bias_samples;
  float az_avg = (float)az_sum / IMU_angle_bias_samples;
  // Use trig to figure out the current pich and roll of the current sesnor
  float IMU_pitch_angle_bias = atan2(-ax_avg, sqrt(ay_avg * ay_avg + az_avg * az_avg));
  float IMU_roll_angle_bias = atan2(ay_avg, az_avg);
  // Apply roll and pitch as scale factor to correctly orientate the sensor at any orientation
  IMU_yaw_scale = cos(IMU_pitch_angle_bias) * cos(IMU_roll_angle_bias);
  #if SENSOR_OUTPUT == 1
  uint8_t IMUangles[12]
  memcpy(IMUangles,     &IMU_pitch_angle_bias, 4);
  memcpy(IMUangles + 4, &IMU_roll_angle_bias, 4);
  memcpy(IMUangles + 8, &IMU_yaw_scale, 4);
  sendSerialFeedback('I', IMUangles, 12);
  #endif
}


  // This uses the same format as Serial commands sent to the arduino but it sends them back to the jetson for live serial update
void sendSerialFeedback(char command, const uint8_t* data, size_t dataLen) {
  // Start and end byte for feedback command
  const uint8_t startByte = 0x02;
  const uint8_t endByte   = 0x03; 
  // Create buffer with serial data
  if (dataLen > 60 || (dataLen > 0 && data == nullptr))
    return;
  uint8_t buf[64];   
  size_t idx = 0;
  // Add start byte, end byte, length byte, command byte, and data bytes into buffer,
  buf[idx++] = startByte; 
  buf[idx++] = dataLen + 1;
  buf[idx++] = command;
  for (size_t i = 0; i < dataLen; i++) { 
    buf[idx++] = data[i];
  }
  buf[idx++] = endByte;
  // Write serial buffer to Serial
  Serial.write(buf, idx);   
}

// This processes the serial buffer and if the buffer passes it's byte checks, it's sent to processMessage() to update data.
void processSerialBuffer() {
  while (Serial.available() > 0) {
    byte b = Serial.read();
    if (!receiving_message) {
        if (b == 0x02) {
            receiving_message = true;
            serial_index = 0;
            expected_length = -1;
        }
    } else {
        if (expected_length == -1) {
            expected_length = b;
            if (expected_length <= 0 || expected_length > MY_SERIAL_BUFFER_SIZE) {
                receiving_message = false; // invalid length
            }
        } else {
            serial_buffer[serial_index++] = b;
            if (serial_index == expected_length + 1) { // +1 for end byte
                if (serial_buffer[serial_index-1] == 0x03) {
                    processMessage(serial_buffer, expected_length);
                } else {
                    Serial.println("End byte not found");
                }
                receiving_message = false;
            } else if (serial_index >= MY_SERIAL_BUFFER_SIZE) {
                // overflow protection
                receiving_message = false;
            }
        }
    }
  }
}
}
