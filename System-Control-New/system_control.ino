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
//Arm setup
//Bucket setup
//Drive setup
//Probably LIDAR setup
//Have classes within these setup places
//The void setup just start all components
//Void loop should be split into several different parts similar to how the catagories are set up
//All saftey in one spot, all data updates in one spot, and all autonomy in one spot.
