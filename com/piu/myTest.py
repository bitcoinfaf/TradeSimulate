# -*- coding: utf-8 -*-
# encoding: utf-8
#!/usr/bin/python

import threading
import time
from decimal import Decimal
import SQLiteManager
from gateAPI import GateIO
from Constants import Constant

#用户ID
OWNER_ID = 1
CURRENCY_OTHER = 'eos'
CURRENCY_BASE = 'usdt'
#买卖方向
SIDE_BUY = 1
SIDE_SELL = 2
#订单状态
STATUS_ACCEPTED = 1
STATUS_HALF_FILLED = 2
STATUS_TOTAL_FILLED = 3
STATUS_CANCELLED = 4
#数据来源
DATA_TYPE_ORDER = 1
DATA_TYPE_TRADE = 2
#业务类型
BIZ_TYPE_BUY_ORDER = 1
BIZ_TYPE_BUY_TRADE = 2
BIZ_TYPE_BUY_CANCEL = 3
BIZ_TYPE_SELL_ORDER = 4
BIZ_TYPE_SELL_TRADE = 5
BIZ_TYPE_SELL_CANCEL = 6
#挂单位置
Last_Distant_Percent = 0.1

## 填写 apiKey APISECRET
apiKey = Constant.apiKey
secretKey = Constant.secretKey
## Provide constants
API_QUERY_URL = Constant.API_QUERY_URL
API_TRADE_URL = Constant.API_TRADE_URL
## Create a gate class instance
gate_query = GateIO(API_QUERY_URL, apiKey, secretKey)
gate_trade = GateIO(API_TRADE_URL, apiKey, secretKey)

def tradeAction(arg):
    while(1):
        ticker = gate_query.ticker(CURRENCY_OTHER + '_' + CURRENCY_BASE)
        #print(ticker)
        time.sleep(10)
        break

def orderAction(arg):
    currencyPair = CURRENCY_OTHER + '_' + CURRENCY_BASE
    #{"eos_usdt":{"decimal_places":4,"min_amount":0.0001,"fee":0.2}}
    while(1):
        ticker = gate_query.ticker(currencyPair)
        #买入订单创建，在挂订单不能超过10个
        buyOrderOpenList = SQLiteManager.queryOrderNotFilled(OWNER_ID, SIDE_BUY, STATUS_ACCEPTED, STATUS_HALF_FILLED)
        if buyOrderOpenList is None or len(buyOrderOpenList) < 10:
            last = ticker.get("last")
            balanceBase = SQLiteManager.checkBalance(OWNER_ID, CURRENCY_BASE)
            balanceId = balanceBase.get("balanceId")
            currentBalance = balanceBase.get("currentBalance")
            buyAmount = balanceBase.get("buyAmount")
            sellAmount = balanceBase.get("sellAmount")
            freezeAmount = balanceBase.get("freezeAmount")
            availableAmount = Decimal(currentBalance) - Decimal(freezeAmount) + (Decimal(sellAmount) - Decimal(buyAmount));
            amount = 100;
            lastFreezeAmount = Decimal(last) * Decimal(amount)
            print('availableAmount:[{}],lastFreezeAmount:[{}]'.format(availableAmount.quantize(Decimal('0.0000')), lastFreezeAmount.quantize(Decimal('0.0000'))))
            #购买力足够，使用事务进行DB操作
            if availableAmount > lastFreezeAmount:
                conn = SQLiteManager.get_conn(SQLiteManager.DB_FILE_PATH)
                orderId = SQLiteManager.insertOrder(conn, OWNER_ID, SIDE_BUY, currencyPair, last, amount, 0, 0, STATUS_ACCEPTED)
                SQLiteManager.updateBalance(conn, OWNER_ID, CURRENCY_BASE, 0, 0, str(lastFreezeAmount.quantize(Decimal('0.0000'))))
                endFreezeAmount = lastFreezeAmount + Decimal(freezeAmount)
                SQLiteManager.insertBalanceLog(conn, OWNER_ID, balanceId, CURRENCY_BASE,
                                               currentBalance, currentBalance, buyAmount, buyAmount,
                                               sellAmount, sellAmount, freezeAmount, str(endFreezeAmount.quantize(Decimal('0.0000'))),
                                               DATA_TYPE_ORDER, orderId, BIZ_TYPE_BUY_ORDER)
                conn.commit()
        #展示已有未成交订单
        #showList(buyOrderOpenList)
        endBalanceBase = SQLiteManager.checkBalance(OWNER_ID, CURRENCY_BASE)
        print(endBalanceBase)
        #卖出订单创建，在挂订单不能超过10个
        sellOrderOpenList = SQLiteManager.queryOrderNotFilled(OWNER_ID, SIDE_SELL, STATUS_ACCEPTED, STATUS_HALF_FILLED)
        if sellOrderOpenList is None or len(sellOrderOpenList) < 10:
            conn = SQLiteManager.get_conn(SQLiteManager.DB_FILE_PATH)
        time.sleep(10)
    #print('the arg is:%s' % arg)

def showList(list):
    if list is not None and len(list) > 0:
        for e in range(len(list)):
            print(list[e])

def main():
    #数据表的创建和资产的初始化在其他地方进行
    SQLiteManager.initData(OWNER_ID, CURRENCY_OTHER, CURRENCY_BASE, 100000)
    #线程A，定时5秒从订单数据表中获取尚未完全成交的订单，检查订单内的币种行情数据是否和订单的可以进行成交，如果可以就创建成交记录，调整资产
    tradeThread = threading.Thread(target=tradeAction,args=('tradeThread',))
    tradeThread.start()
    #线程B，检查指定的币种行情数据，决定是否创建订单，是否取消订单
    orderThread = threading.Thread(target=orderAction,args=('orderThread',))
    orderThread.start()

if __name__ == '__main__':
    main()
