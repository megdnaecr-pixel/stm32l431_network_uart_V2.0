/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
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
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "can.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */
#define UNINIT            0

unsigned int CRC_16_Calc_TX(unsigned char* ptr, int count);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
unsigned char crcHigh1=0,crcLow1=0;
unsigned char crcLow2=0;
union
{
   unsigned char bytes[5];
  struct
  {
    uint8_t heaer1;
    uint8_t heaer2;
    uint8_t CMD;
    uint8_t  CRC1;
    uint8_t  CRC2;

  } data;

} GP;

uint8_t Relay_BUF[5]={0};
static volatile unsigned char Relay_Index = 0;
char crc_Relay=0;

static volatile uint8_t step_rudders= 0;
volatile long RUD_byte_cnt=0;

/* --- Output channel table: maps each command pair to a GPIO --- */
typedef struct {
	GPIO_TypeDef *port;
	uint16_t      pin;
} OutputPin_t;

static const OutputPin_t outputMap[NUM_OUTPUT_CHANNELS] = {
	{ GPIO1_Port, GPIO1_Pin },   /* CMD_1 -> PA9  */
	{ GPIO2_Port, GPIO2_Pin },   /* CMD_2 -> PA10 */
	{ GPIO3_Port, GPIO3_Pin },   /* CMD_3 -> PA4  */
	{ GPIO4_Port, GPIO4_Pin },   /* CMD_4 -> PA5  */
	{ LED1_GPIO_Port, LED1_Pin },/* CMD_5 -> PB6  */
};

/**
  * @brief  Execute a command: route On/Off to the correct GPIO output
  */
static void ExecuteCommand(uint8_t cmd)
{
	int ch = -1;               /* channel index into outputMap */
	GPIO_PinState state;

	switch (cmd)
	{
		case CMD_1_On:  ch = 0; state = GPIO_PIN_SET;   break;
		case CMD_1_Off: ch = 0; state = GPIO_PIN_RESET; break;
		case CMD_2_On:  ch = 1; state = GPIO_PIN_SET;   break;
		case CMD_2_Off: ch = 1; state = GPIO_PIN_RESET; break;
		case CMD_3_On:  ch = 2; state = GPIO_PIN_SET;   break;
		case CMD_3_Off: ch = 2; state = GPIO_PIN_RESET; break;
		case CMD_4_On:  ch = 3; state = GPIO_PIN_SET;   break;
		case CMD_4_Off: ch = 3; state = GPIO_PIN_RESET; break;
		case CMD_5_On:  ch = 4; state = GPIO_PIN_SET;   break;
		case CMD_5_Off: ch = 4; state = GPIO_PIN_RESET; break;
		default:        return;  /* unknown command -- ignore */
	}

	HAL_GPIO_WritePin(outputMap[ch].port, outputMap[ch].pin, state);
}

void GPIO_Set_Action(void)
{
	for (int i=0;i<5;++i)
	{
		GP.bytes[i]=Relay_BUF[i];
	}

	ExecuteCommand(GP.data.CMD);

	/* Send ACK back on CAN with same command byte */
	CAN_SendProtocolMsg(GP.data.CMD);
}

void RUDDERS_HEAD_Parse_Character(uint8_t c)
{
	RUD_byte_cnt++;
	switch (step_rudders)
	{

	case 0:
		if(c!=0xCC)
			goto error;
		step_rudders++;
		Relay_Index=0;
		Relay_BUF[Relay_Index]=c;
		Relay_Index++;

	break;
	case 1:
		if(c!=0xBA)
			goto error;

		step_rudders++;

		Relay_BUF[Relay_Index]=c;
		Relay_Index++;

	break;
	case 2:

		Relay_BUF[Relay_Index]=c;
		Relay_Index++;

		if( Relay_Index==3)
		{

			CRC_16_Calc_TX(Relay_BUF ,3);
			Relay_BUF[3]=crcLow2;
			Relay_BUF[4]=crcHigh1;
			crc_Relay=0;
			step_rudders++;

		}

	break;
	case 3:
		if (crc_Relay== 0)
		{
			if (c != crcLow2)
				goto error;
			else
			{
				crc_Relay++;
			}
		}
		else if (c != crcHigh1)
		{
			goto error;
		}
		else
		{
			GPIO_Set_Action();
			goto restart;
		}
	break;

	}
	return;

error:

restart:

	step_rudders = UNINIT;
	RUD_byte_cnt = 0;
	Relay_Index=0;
	return;

}

unsigned int CRC_16_Calc_TX(unsigned char* ptr, int count)
{
	/**
	*
	* \param ptr memory address where data
	* \param count
	*
	* \return calculated CRC for the
	*
	* g(X) = X^16 + X^12 + X^5 + 1 ---> 0x1021
	*
	*/
	unsigned int crc, i;
	unsigned int Temp;
	crc = 0;
	while (--count >= 0)
	{
		Temp = (int) * ptr;
		Temp <<= 8;
		ptr++;
		crc = crc ^ Temp;
		for (i = 0; i < 8; ++i)
		{
			if (crc & 0x8000)
			{
				crc <<= 1 ;
				crc ^= 0x1021;
			}
			else
			{
				crc <<= 1;
			}
		}
	}
	crc=crc & 0x3FFF;
	crcLow1=(crc&0x7F);
	crcHigh1=((crc>>7)&0x7F);
	crc=crcHigh1;
	crc=(crc<<8)|crcLow1;
	crcLow2=crc;
	return (crc&0xffff);
}

/**
  * @brief  إرسال رسالة عبر CAN بنفس بروتوكول الاستقبال
  * @param  cmd: بايت الأمر المراد إرساله
  * الإطار: [0xCC][0xBA][CMD][CRC_Low][CRC_High]
  */
void CAN_SendProtocolMsg(uint8_t cmd)
{
	CAN_TxHeaderTypeDef txHeader;
	uint8_t             txData[5];
	uint32_t            txMailbox;

	/* بناء الإطار */
	txData[0] = 0xCC;
	txData[1] = 0xBA;
	txData[2] = cmd;

	/* حساب CRC على 3 بايتات أولى */
	CRC_16_Calc_TX(txData, 3);
	txData[3] = crcLow2;
	txData[4] = crcHigh1;

	/* ضبط رأس رسالة الإرسال */
	txHeader.StdId              = CAN_TX_STD_ID;
	txHeader.ExtId              = 0;
	txHeader.RTR                = CAN_RTR_DATA;
	txHeader.IDE                = CAN_ID_STD;
	txHeader.DLC                = 5;
	txHeader.TransmitGlobalTime = DISABLE;

	HAL_CAN_AddTxMessage(&hcan1, &txHeader, txData, &txMailbox);
}
/**
  * @brief  CAN RX FIFO0 message pending callback
  *         Called when a CAN message is received
  */
void HAL_CAN_RxFifo0MsgPendingCallback(CAN_HandleTypeDef *hcan)
{
	CAN_RxHeaderTypeDef rxHeader;
	uint8_t rxData[8];

	if (HAL_CAN_GetRxMessage(hcan, CAN_RX_FIFO0, &rxHeader, rxData) == HAL_OK)
	{
		for (uint8_t i = 0; i < rxHeader.DLC; i++)
		{
			RUDDERS_HEAD_Parse_Character(rxData[i]);
		}
	}
}

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_CAN1_Init();         /* CAN init FIRST (like working project) */
  /* USER CODE BEGIN 2 */

  HAL_GPIO_WritePin(LED1_GPIO_Port, LED1_Pin, GPIO_PIN_RESET);

  /* === CAN FILTER CONFIG (inline, same as working project) === */
  {
    CAN_FilterTypeDef canFilterConfig;
    canFilterConfig.FilterBank = 0;
    canFilterConfig.FilterMode = CAN_FILTERMODE_IDMASK;
    canFilterConfig.FilterScale = CAN_FILTERSCALE_32BIT;
    canFilterConfig.FilterIdHigh = 0x0000;
    canFilterConfig.FilterIdLow = 0x0000;
    canFilterConfig.FilterMaskIdHigh = 0x0000;
    canFilterConfig.FilterMaskIdLow = 0x0000;
    canFilterConfig.FilterFIFOAssignment = CAN_RX_FIFO0;
    canFilterConfig.FilterActivation = ENABLE;
    canFilterConfig.SlaveStartFilterBank = 14;

    if (HAL_CAN_ConfigFilter(&hcan1, &canFilterConfig) != HAL_OK)
    {
      Error_Handler();
    }
  }

  /* === CAN START (inline, same as working project) === */
  if (HAL_CAN_Start(&hcan1) != HAL_OK)
  {
    Error_Handler();
  }

  if (HAL_CAN_ActivateNotification(&hcan1, CAN_IT_RX_FIFO0_MSG_PENDING) != HAL_OK)
  {
    Error_Handler();
  }

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  if (HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = 1;
  RCC_OscInitStruct.PLL.PLLN = 10;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV7;
  RCC_OscInitStruct.PLL.PLLQ = RCC_PLLQ_DIV2;
  RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_4) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
