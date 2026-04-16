/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32l4xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);
void CAN_SendProtocolMsg(uint8_t cmd);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define LED1_Pin GPIO_PIN_6
#define LED1_GPIO_Port GPIOB

/* CAN Transmit Standard ID (يمكن تغييره حسب الشبكة) */
#define CAN_TX_STD_ID   0x100U

/* USER CODE BEGIN Private defines */
enum CmdDriverBox1
{
	FIRE_On          =0x01,
	FIRE_Off         =0x02,
	Cmd_On_70S       =0x03,
	Cmd_Off_70S      =0x04,
	Engine_CMD_On    =0x05,
	Engine_CMD_Off   =0x06,
	SEP_CMD_On       =0x07,
	SEP_CMD_Off      =0x08,
	E_CUT_Cmd_On     =0x09,
	E_CUT_Cmd_Off    =0x0A,
	ABD_Cmd_On       =0x0B,
	ABD_Cmd_Off      =0x0C,
	Boost_Off        =0x0D,
	Boost_On         =0x0E,
	Batt_Off         =0x0F,
	Tele_Off         =0x10,
	Tele_On          =0x11,

};
/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
