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
	CMD_1_On         =0x01,
	CMD_1_Off        =0x02,
	CMD_2_On         =0x03,
	CMD_2_Off        =0x04,
	CMD_3_On         =0x05,
	CMD_3_Off        =0x06,
	CMD_4_On         =0x07,
	CMD_4_Off        =0x08,
	CMD_5_On         =0x09,
	CMD_5_Off        =0x0A,
	CMD_6_On         =0x0B,
	CMD_6_Off        =0x0C,
	CMD_7_Off        =0x0D,
	CMD_7_On         =0x0E,
	CMD_8_Off        =0x0F,
	CMD_9_Off        =0x10,
	CMD_9_On         =0x11,

};
/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
