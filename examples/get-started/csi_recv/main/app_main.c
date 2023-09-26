/* Get Start Example

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied.
*/
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

#include "nvs_flash.h"

#include "esp_mac.h"
#include "rom/ets_sys.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_now.h"
#include "esp_sleep.h"

#include <esp_http_server.h>

#if CONFIG_STATION_MODE
#define ESPNOW_WIFI_MODE WIFI_MODE_STA
#define ESPNOW_WIFI_IF   ESP_IF_WIFI_STA
#else
#define ESPNOW_WIFI_MODE WIFI_MODE_AP
#define ESPNOW_WIFI_IF   ESP_IF_WIFI_STA
//#define ESPNOW_WIFI_IF   ESP_IF_WIFI_AP
#endif

#define CONFIG_LESS_INTERFERENCE_CHANNEL    11
#define CONFIG_SEND_FREQUENCY               100
//#define CONFIG_SEND_FREQUENCY               1

//static const uint8_t CONFIG_CSI_SEND_MAC[] = {0x1a, 0x00, 0x00, 0x00, 0x00, 0x00};
static const uint8_t CONFIG_CSI_SEND_MAC[] = {0x84, 0xf7, 0x03, 0xd7, 0x97, 0x64};

static const char *TAG = "csi_recv";

//static xQueueHandle submit_queue;
struct QueueDefinition *submit_queue;

//84:f7:03:d7:97:65

typedef struct _csi_queue
{
    // wifi_csi_info_t
    char               *info;
    //char                *ctx;
}  csi_queue;


void procq(void *ctx, wifi_csi_info_t *info)
{
    static int s_count = 0;

    const wifi_pkt_rx_ctrl_t *rx_ctrl = &info->rx_ctrl;

    //memcpy(rx_ctrl, &info->rx_ctrl, sizeof(wifi_pkt_rx_ctrl_t);

    if (!s_count) {
        ESP_LOGI(TAG, "================ CSI RECV ================");
        ets_printf("type,id,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,not_sounding,aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,channel,secondary_channel,local_timestamp,ant,sig_len,rx_state,len,first_word,data\n");
    }


    ets_printf("CSI_DATA,%d," MACSTR ",%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d",
            s_count++, MAC2STR(info->mac), rx_ctrl->rssi, rx_ctrl->rate, rx_ctrl->sig_mode,
            rx_ctrl->mcs, rx_ctrl->cwb, rx_ctrl->smoothing, rx_ctrl->not_sounding,
            rx_ctrl->aggregation, rx_ctrl->stbc, rx_ctrl->fec_coding, rx_ctrl->sgi,
            rx_ctrl->noise_floor, rx_ctrl->ampdu_cnt, rx_ctrl->channel, rx_ctrl->secondary_channel,
            rx_ctrl->timestamp, rx_ctrl->ant, rx_ctrl->sig_len, rx_ctrl->rx_state);

    ets_printf(",%d,%d,\"[%d", info->len, info->first_word_invalid, info->buf[0]);

    for (int i = 1; i < info->len; i++) {
        ets_printf(",%d", info->buf[i]);
    }

    ets_printf("]\"\n\n");
}

static  void    write_worker(void *pvParameter)

{
    while(1)
        {
        csi_queue evt;

        while (xQueueReceive(submit_queue, &evt, portMAX_DELAY) == pdTRUE)
            {
            procq(NULL, (wifi_csi_info_t*)evt.info);
            free(evt.info);
            //free(evt.ctx);
            }
        }
}

static void wifi_init()
{
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    ESP_ERROR_CHECK(esp_netif_init());
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_bandwidth(ESP_IF_WIFI_STA, WIFI_BW_HT40));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_ERROR_CHECK(esp_wifi_config_espnow_rate(ESP_IF_WIFI_STA, WIFI_PHY_RATE_MCS0_SGI));
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));

    ESP_ERROR_CHECK(esp_wifi_set_channel(CONFIG_LESS_INTERFERENCE_CHANNEL, WIFI_SECOND_CHAN_BELOW));
    //ESP_ERROR_CHECK(esp_wifi_set_mac(WIFI_IF_STA, CONFIG_CSI_SEND_MAC));
}

//wifi_pkt_rx_ctrl_t rx_ctrl;

static void wifi_csi_rx_cb(void *ctx, wifi_csi_info_t *info)
{
    if (!info || !info->buf) {
        ESP_LOGW(TAG, "<%s> wifi_csi_cb", esp_err_to_name(ESP_ERR_INVALID_ARG));
        return;
    }

    if (memcmp(info->mac, CONFIG_CSI_SEND_MAC, 6)) {
        return;
    }

    if (!uxQueueSpacesAvailable(submit_queue))
        return;

    csi_queue  evt;

    //#define WANT 1024

    evt.info = malloc(sizeof(wifi_csi_info_t) + 2);
    if(!evt.info)
        return;

    memcpy(evt.info, info, sizeof(wifi_csi_info_t));

    //printf("tx %p len %d\n", ctx, info->len);

    //evt.ctx = malloc(info->len + 1);
    //if(!evt.ctx)
    //    return;
    //  if (ctx)
    //    {
    //    memcpy(evt.ctx, ctx, info->len);
    //    }
    //if (xQueueSend(submit_queue, &evt, 1000 / portTICK_PERIOD_MS) != pdTRUE)
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    if (xQueueSendFromISR(submit_queue, &evt, &xHigherPriorityTaskWoken) != pdTRUE)
        {
        ESP_LOGE(TAG, "Submit to queue failed.");
        //ret = -2;
        }
    }

static void wifi_csi_init()
{
    ESP_ERROR_CHECK(esp_wifi_set_promiscuous(true));
    // ESP_ERROR_CHECK(esp_wifi_set_promiscuous_rx_cb(g_wifi_radar_config->wifi_sniffer_cb));

    /**< default config */
    wifi_csi_config_t csi_config = {
        .lltf_en           = true,
        .htltf_en          = true,
        .stbc_htltf2_en    = true,
        .ltf_merge_en      = true,
        .channel_filter_en = true,
        .manu_scale        = false,
        .shift             = false,
    };
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&csi_config));
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(wifi_csi_rx_cb, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_csi(true));
}

void  send_thread(void *arg)
{
 /**
     * @breif Initialize ESP-NOW
     *        ESP-NOW protocol see: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_now.html
     */
    ESP_ERROR_CHECK(esp_now_init());
    ESP_ERROR_CHECK(esp_now_set_pmk((uint8_t *)"pmk1234567890123"));

    esp_now_peer_info_t peer = {
        .channel   = CONFIG_LESS_INTERFERENCE_CHANNEL,
        .ifidx     = WIFI_IF_STA,
        .encrypt   = false,
        .peer_addr = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff},
    };
    ESP_ERROR_CHECK(esp_now_add_peer(&peer));

    ESP_LOGI(TAG, "================ CSI SEND ================");
    ESP_LOGI(TAG, "wifi_channel: %d, send_frequency: %d, mac: " MACSTR,
             CONFIG_LESS_INTERFERENCE_CHANNEL, CONFIG_SEND_FREQUENCY, MAC2STR(CONFIG_CSI_SEND_MAC));

    for (uint8_t count = 0; ;++count) {
        esp_err_t ret = esp_now_send(peer.peer_addr, &count, sizeof(uint8_t));

        if(ret != ESP_OK) {
            ESP_LOGW(TAG, "<%s> ESP-NOW send error", esp_err_to_name(ret));
        }
        //ESP_LOGI(TAG, "%d ",   count);
        usleep(1000 * 1000 / CONFIG_SEND_FREQUENCY);
    }
}

void app_main()
{
    //Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
      ESP_ERROR_CHECK(nvs_flash_erase());
      ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    wifi_init();

    submit_queue = xQueueCreate(3, sizeof(csi_queue));
    xTaskCreate(write_worker, "write_worker", 3048, NULL, 4, NULL);

    wifi_csi_init();

    uint8_t vvv[ESP_NOW_ETH_ALEN];
    esp_wifi_get_mac(ESPNOW_WIFI_IF, vvv);

    printf("mac: " MACSTR "\n", MAC2STR(vvv));
    //usleep(3000 * 1000);

    //xTaskCreate(send_thread, "send_thread", 4024, NULL, 2, NULL);
}
