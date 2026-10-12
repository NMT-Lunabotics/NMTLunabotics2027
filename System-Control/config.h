#pragma once
#ifndef CONFIG_H
#define CONFIG_H

#define MAIN_ROBOT 0 // BERMINATOR settings=0, NUC settings=1 //Sets robot state to what robot is being used
#define PCB_BOARD_SCHEMATIC 0 // BERMINATOR=0 //Sets PCB board schem to the current robot

//------------------------------------------------------------
//        MAIN ROBOT SETTINGS (REGULUS and BERMINATOR)
//------------------------------------------------------------
#if MAIN_ROBOT==0
  // List of components flags to enable/disable for testing
  #define STATE_LEDS_ENABLED           1
  #define MOTORS_ENABLED               1
  #define BUCKET_ACTUATOR_ENABLED      1
  #define ARM_ACTUATORS_ENABLED        1
  #define SERVO_MOTOR_ENABLED          0
  #define IMU_SENSOR_ENABLED           0
  #define IBUS_RECIVER_ENABLED         1
  // List of faults to disable
  #define COMPONENT_TIMEOUT_FAULTS     0 //1
  // Debug mode flags
  #define DEBUG_MODE                   0
  #define SENSOR_OUTPUT                0 // 1: IMU, 2: IBUS, 3: IBUS raw, 4: Final IBUS commands, 5: Actuator positions, 6: Actuator pot values, 8: Servo angle
#else
//------------------------------------------------------------
//                    NUC ROBOT SETTINGS
//------------------------------------------------------------
  #define ERROR_LEDS_ENABLED           0
  #define MOTORS_ENABLED               1
  #define BUCKET_ACTUATOR_ENABLED      0
  #define ARM_ACTUATORS_ENABLED        0
  #define SERVO_MOTOR_ENABLED          1
  #define IMU_SENSOR_ENABLED           0
  #define IBUS_RECIVER_ENABLED         0
  #define SERIAL_COMM_TIMEOUT_FAULT    1
  #define COMPONENT_TIMEOUT_FAULTS     0
  #define DEBUG_MODE                   0
  #define SENSOR_OUTPUT                0  
#endif

#endif
