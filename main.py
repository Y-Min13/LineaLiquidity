import src.Helpers.helper as helper
import src.networks as nt
import settings
import src.Swaps.swapOps as swapOps
import random
import src.logger as logger
import src.Exchanges.okxOperations as okxOp
import src.Helpers.gasPriceChecker as gPC
import src.Helpers.userHelper as userHelper
from threading import Thread
import src.Bridges.stargateBridge as stargateBridge


logger.create_xml()
settings.last_row = logger.get_last_row_overall()
wallets = helper.read_wallets()

net_src = nt.arbitrum_net


def main():
    op = 1
    if settings.wallet_mode == 2:
        random.shuffle(wallets)
    for wallet in wallets:
        balance_st = nt.linea_net.web3.from_wei(nt.linea_net.web3.eth.get_balance(wallet.address), 'ether')
        logger.cs_logger.info(f'')
        logger.cs_logger.info(
            f'№ {op} ({wallet.wallet_num})  Адрес: {wallet.address}  Биржа: {wallet.exchange_address}')
        script_time = helper.get_curr_time()

        # Вывод с биржи
        if settings.exc_withdraw == 1:
            res, rc = okxOp.withdraw(wallet, nt.linea_net)
            if int(rc) > 0:
                logger.cs_logger.info(f'{res}')
                break

            balance_end = nt.linea_net.web3.from_wei(nt.linea_net.web3.eth.get_balance(wallet.address), 'ether')
            nonce = nt.linea_net.web3.eth.get_transaction_count(wallet.address)
            logger.write_overall(wallet, balance_st, balance_end, script_time, nonce)


        # Свапы
        gPC.check_limit()
        swapOps.swaps(wallet)

        balance_end = nt.linea_net.web3.from_wei(nt.linea_net.web3.eth.get_balance(wallet.address), 'ether')
        nonce = nt.linea_net.web3.eth.get_transaction_count(wallet.address)
        if settings.exc_withdraw == 0:
            logger.write_overall(wallet, balance_st, balance_end, script_time, nonce)
        else:
            logger.rewrite_overall(wallet, balance_end, nonce)

        # Депозит на биржу или бридж
        if settings.exc_deposit == 1:
            if settings.switch_bridge_exc == 0:
                # Трансфер средств на адрес биржи в Linea
                okxOp.deposit(wallet, nt.linea_net)
                balance_end = nt.linea_net.web3.from_wei(nt.linea_net.web3.eth.get_balance(wallet.address), 'ether')
                nonce = nt.linea_net.web3.eth.get_transaction_count(wallet.address)
                logger.rewrite_overall(wallet, balance_end, nonce)

            if settings.switch_bridge_exc == 1:
                # Делаем бридж в Arbitrum или Optimism
                result = stargateBridge.bridge_eth(wallet, nt.linea_net, net_src, True)

                if result is True:
                    balance_end = nt.linea_net.web3.from_wei(nt.linea_net.web3.eth.get_balance(wallet.address), 'ether')
                    nonce = nt.linea_net.web3.eth.get_transaction_count(wallet.address)
                    logger.rewrite_overall(wallet, balance_end, nonce)
                    # Трансфер средств на адрес биржи в Arbitrum
                    okxOp.deposit(wallet, net_src)
                    logger.rewrite_overall(wallet, balance_end, nonce)
                else:
                    logger.cs_logger.info(f'Бридж не удался')


#'''
logger.cs_logger.info(f'Найдено кошельков: {len(wallets)}')
userHelper.get_info(wallets)
if settings.start_flag is True:
    gPC.check_gas_price_ether()
    check_thread = Thread(target=gPC.checking, args=(), daemon=True)
    main_thread = Thread(target=main, args=())
    check_thread.start()
    main_thread.start()
    main_thread.join()
    logger.cs_logger.info(f'Выход...')
#'''
