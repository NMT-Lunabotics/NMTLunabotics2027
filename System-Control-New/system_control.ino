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

  //----------------------------------------------------------------------------------
  //                           Bucket Actuators Setup
  //----------------------------------------------------------------------------------
//all the same stuff as arm actuator set-up but for the single bucket actuator.
  //----------------------------------------------------------------------------------
  //                             Drive Motor Setup
  //----------------------------------------------------------------------------------
#if MAIN_ROBOT = BERM
  //Define motor pins
  const int LEFT_MOTOR_PIN = X
  const int RIGHT_MOTOR_PIN = X
  const int COMMON_PIN = X
#endif


  //----------------------------------------------------------------------------------
  //                               LIDAR Setup
  //----------------------------------------------------------------------------------

  //----------------------------------------------------------------------------------
  //                        LED System, IBUS and IMU Setup
  //----------------------------------------------------------------------------------

  //----------------------------------------------------------------------------------
  //                             System Variables
  //----------------------------------------------------------------------------------
  
  //----------------------------------------------------------------------------------
  //                            Subsystem Classes Setup
  //----------------------------------------------------------------------------------

//The void setup just start all components
void setup(){
}
//Void loop should be split into several different parts similar to how the catagories are set up
//All saftey in one spot, all data updates in one spot, and all autonomy in one spot.
void loop(){
}
