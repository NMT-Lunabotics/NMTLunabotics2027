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
  //----------------------------------------------------------------------------------
  //                            Subsystem Classes Setup
  //----------------------------------------------------------------------------------
// Did it in the main actuators and motors channels, felt more readable if it was just commented as a class

//The void setup just start all components
void setup(){
}
//Void loop should be split into several different parts similar to how the catagories are set up
//All saftey in one spot, all data updates in one spot, and all autonomy in one spot.
void loop(){
}
