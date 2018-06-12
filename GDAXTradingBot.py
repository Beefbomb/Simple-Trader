#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gdax
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import traceback
import sys
import argparse

time_interval_between_polling_in_seconds = .45

k_window = 2400
d_window = 90
d_n_window = 90

list_of_prices_for_averages = list()
percent_k_list = list()
percent_d_list = list()
percent_d_n_list = list()

# This is required as a cache    
previous_percent_k = 0.5

# Tolerance in case the price fluctuates only a little bit
percent_k_price_tolerance = .001

#
buy_queue = list()
sell_queue = list()

standard_order_size = 0.01


def main(pair, k, d, dn, interval, amount):
    global buy_queue
    global sell_queue
    global standard_order_size
    global time_interval_between_polling_in_seconds
    key = # INSERT KEY HERE
    b64secret = # INSERT SECRET HERE
    passphrase = # INSERT PASSPHRASE HERE
    
    #target_symbol_pair = 'LTC-USD'
    #target_symbol_pair = 'ETH-USD'
    #target_symbol_pair = 'BTC-USD'
    #minimum_btc_order_size = '0.05'
    
    target_symbol_pair = pair
    k_window = k
    d_window = d
    d_n_window = dn
    time_interval_between_polling_in_seconds = interval
    standard_order_size = amount
    
    print("Target Trading Pair: {}".format(target_symbol_pair))
    print("%K:  {}".format(k_window))
    print("%D:  {}".format(d_window))
    print("%Dn: {}".format(d_n_window))
    print("Polling Interval: {}".format(time_interval_between_polling_in_seconds))
    print("Amount: {}".format(amount))
    
        
    auth_client = gdax.AuthenticatedClient(key, b64secret, passphrase)

    accounts = auth_client.get_accounts()
    print(accounts)
    
    print("Balances")
    for entry in accounts:
        print("Currency: {}, Balance: {}".format(entry['currency'], entry['balance']))
        
    xdata = list(range(50))
    ydata = [0] * 50
    
    xdata2 = list(range(50))
    ydata2 = [0] * 50
    
    plt.show()
    axes = plt.gca()
    axes.set_xlim(0, 50)
    axes.set_ylim(0, +100)
    line, line2 = axes.plot(xdata, ydata, 'g-', xdata2, ydata2, 'r-')
    

    
    while True:
        try:
            time.sleep(time_interval_between_polling_in_seconds)
            price = getPrice(auth_client, target_symbol_pair)
            #print(price)
            list_of_prices_for_averages.append(price)
            
            current_position = len(list_of_prices_for_averages)
            
            # Update %k
            if len(list_of_prices_for_averages) >= k_window:
                
                sub_list = list_of_prices_for_averages[(current_position - k_window):current_position]
                percent_k = _calculatePercentK(sub_list)
                percent_k_list.append(percent_k)
                #print("%K: {}".format(percent_k))
                
                #line1.set_ydata(percent_k)
            else:
                percent_k_list.append(0)
            
            # Update %D
            if len(list_of_prices_for_averages) >= (k_window + d_window):

                sub_list = percent_k_list[(current_position - d_window):current_position]
                percent_d = float(sum(sub_list) / d_window)
                percent_d_list.append(percent_d)
                #print("%D: {}".format(percent_d))
                
                #if len(xdata) < 50:
                #    xdata.append(current_position)
                
                ydata.append(percent_d)
                
                if len(ydata) > 50:
                    ydata.pop(0)

            else:
                percent_d_list.append(0)
                
            # Update %Dn
            if len(list_of_prices_for_averages) >= (k_window + d_window + d_n_window):

                sub_list = percent_d_list[(current_position - d_n_window):current_position]
                percent_d_n = float(sum(sub_list) / d_n_window)
                percent_d_n_list.append(percent_d_n)
                #print("%Dn: {}".format(percent_d_n))
                
                #print(percent_k_list)
                #print(percent_d_list)
                #print(percent_d_n_list)
                
                ydata2.append(percent_d_n)
                
                if len(ydata2) > 50:
                    ydata2.pop(0)
                
                line.set_xdata(xdata)
                line.set_ydata(ydata)
                
                line2.set_xdata(xdata2)
                line2.set_ydata(ydata2)
                plt.draw()
                plt.pause(1e-17)
                #time.sleep(0.1)
                
                print("${:.2f} - %k: {} %D: {} %Dn: {}".format(price, percent_k_list[-1], percent_d_list[-1], percent_d_n_list[-1]))
                sys.stderr.write("\n${:.2f} - %k: {} %D: {} %Dn: {}".format(price, percent_k_list[-1], percent_d_list[-1], percent_d_n_list[-1]))
            else:
                print("${:.2f}".format(price))
                percent_d_n_list.append(0)
                
            # Make sure there are at least 2 entries for %Dn
            if len(list_of_prices_for_averages) >= (k_window + d_window + d_n_window + 1):
                # See if we cross above or below the thresholds.
                
                d_prev = percent_d_list[-2]
                d_curr = percent_d_list[-1]
                
                d_n_prev = percent_d_n_list[-2]
                d_n_curr = percent_d_n_list[-1]
                
                # Check if D crossed under Dn
                if (d_prev >= d_n_prev) and (d_curr < d_n_curr):
                    
                    # Check if intersection is above thresholds
                    if d_curr > 80:
                        print("[Selling]")
                        sys.stderr.write("[Selling]")
                        
                        order_size = 1
                        # See how many buy orders we can eliminate
                        #for buy_order in buy_queue:
                        #    if price > buy_order:
                        #        order_size += 1
                        #    if order_size >= 3:
                        #        break
                        
                        print("Before - Buy Queue: {}".format(buy_queue))
                        print("Before - Sell Queue: {}".format(sell_queue))
                        issueMarketSell(auth_client, order_size, target_symbol_pair)
                        print("After - Buy Queue: {}".format(buy_queue))
                        print("After - Sell Queue: {}".format(sell_queue))
                
                
                # Check if D crossed over Dn
                if (d_prev <= d_n_prev) and (d_curr > d_n_curr):
                
                    # Check if intersection is below thresholds
                    if d_curr < 20:
                        print("[Buying]")
                        sys.stderr.write("[Buying]")
                        
                        order_size = 1
                        # See how many sell orders we can eliminate
                        #for sell_order in sell_queue:
                        #    if price < sell_order:
                        #        order_size += 1
                        #    if order_size >= 3:
                        #        break
                        
                        print("Before - Buy Queue: {}".format(buy_queue))
                        print("Before - Sell Queue: {}".format(sell_queue))
                        issueMarketBuy(auth_client, order_size, target_symbol_pair)
                        print("After - Buy Queue: {}".format(buy_queue))
                        print("After - Sell Queue: {}".format(sell_queue))
                        
                        
        except KeyboardInterrupt:
            print("Aborting...")
            break
        except:
            print("Unexpected error: {}".format(sys.exc_info()[0]))
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
        
    # Calculate End
    updated_accounts = auth_client.get_accounts()
    print("Updated Balances")
    print("Currency: {}, Balance: {}".format(entry['currency'], entry['balance']))
    
    for entry in updated_accounts:
        print("\nDifferences")
        
    for new_entry in updated_accounts:
        
        for old_entry in accounts:
            
            if new_entry['currency'] == old_entry['currency']:
                difference = float(new_entry['balance']) - float(old_entry['balance'])
                print("Currency: {}, Balance Difference: {}".format(new_entry['currency'], difference))
                break
    
def issueMarketBuy(client, units, target_symbol_pair):
    order_size = standard_order_size * units
    order_size = float('{:.8f}'.format(order_size))
    buy_order = client.buy(size=order_size, type='market', product_id=target_symbol_pair)
    buy_id = buy_order['id']
    
    # Poll until finished
    finished_order = False
    
    average_price = 0.0
    
    while not finished_order:
        # Delay a little for the order to process
        time.sleep(0.25)
        
        order_status = client.get_fills(order_id=buy_id)
        
        for status in order_status:
            
            average_price = 0.0
            
            all_settled = True
            for entry in status:
                print(entry)
                settled_status = entry['settled']
                price = float(entry['price'])
                size = float(entry['size'])
                
                all_settled = all_settled and settled_status
                print("Price: {} Settled: {}".format(price, settled_status))
                
                average_price += price * size
            
            # We have to make sure that order_status has at least 1 entry
            if status:
                finished_order = all_settled
            
            if finished_order:
                print("Pre-Average Price: {}, Order Size: {}".format(average_price, order_size))
                sys.stderr.write("Pre-Average Price: {}, Order Size: {}".format(average_price, order_size))
                average_price = average_price / order_size
                break
                
    
    
    print("\tUnits: {} Average Price: {}".format(units, average_price))
                
    # Bought at 250  
    # Sold at [100, 200, 300, 400]            
    # See if we bought anything lower than a sell price
    # Iterate from the lowest sells, to the highest sells
    remaining_units = units
    index_list_to_remove = []
    for index, sell_price in (enumerate(sell_queue)):
        
        # DOUBLE CHECK THIS LOGIC!
        # If there's nothing left to cancel out, we're done, and can bail from this function
        if remaining_units == 0:
            break
            
        if sell_price > average_price:
            #print("Sell Price: {} Average Price: {}".format(sell_price, average_price))
            # Might need to subtract 1 for index here????
            index_list_to_remove.insert(0, index)
            remaining_units -= 1
                
    # Actually remove the items now
    for index in index_list_to_remove:
        #print("Sell Queue - Removing Index: {}".format(index))
        sell_queue.pop(index)
            
    # go from left to right, and add the item
    for index, item in enumerate(buy_queue):
        if average_price < item:
            for num in range(remaining_units):
                buy_queue.insert(index, average_price)
            return
    
    # If we've cycled through the entire list, and it's made it this far, we add it at the end
    for num in range(remaining_units):
        buy_queue.append(average_price)
    return
          
def issueMarketSell(client, units, target_symbol_pair):

    order_size = standard_order_size * units
    order_size = float('{:.8f}'.format(order_size))
    sell_order = client.sell(size=order_size, type='market', product_id=target_symbol_pair)
    print(sell_order)
    sell_id = sell_order['id']
    
    # Poll until finished
    finished_order = False
    
    average_price = 0.0
    
    while not finished_order:
        # Delay a little for the order to process
        time.sleep(0.25)
        
        order_status = client.get_fills(order_id=sell_id)
        
        for status in order_status:
            
            average_price = 0.0
            
            all_settled = True
            for entry in status:
                print(entry)
                settled_status = entry['settled']
                price = float(entry['price'])
                size = float(entry['size'])
                
                all_settled = all_settled and settled_status
                print("Price: {} Settled: {}".format(price, settled_status))
                
                average_price += price * size
                
            # We have to make sure that order_status has at least 1 entry
            if status:
                finished_order = all_settled
            
            if finished_order:
                print("Pre-Average Price: {}, Order Size: {}".format(average_price, order_size))
                sys.stderr.write("Pre-Average Price: {}, Order Size: {}".format(average_price, order_size))
                average_price = average_price / order_size
                break
    
    # See if we can cancel out any entries from the buy order list
    remaining_units = units
    #print("Remaining Units: {}".format(remaining_units))
    print("\tUnits: {} Average Price: {}".format(units, average_price))
    
    # Iterate through list, and find the highest buys we can cancel out with our sell
    index_list_to_remove = []
    for index, buy_price in reversed(list(enumerate(buy_queue))):
        
        # DOUBLE CHECK THIS LOGIC!
        # If there's nothing left to cancel out, we're done, and can bail from this function
        if remaining_units == 0:
            break
            
        if buy_price < average_price:
            #print("Buy Price: {} Average Price: {}".format(buy_price, average_price))
            # Might need to subtract 1 for index here????
            index_list_to_remove.append(index)
            remaining_units -= 1
                
    # Actually remove the items now
    for index in index_list_to_remove:
        #print("Buy Queue - Removing Index: {}".format(index))
        buy_queue.pop(index)
    
    # go from left to right, and add the item
    for index, item in enumerate(sell_queue):
        if average_price < item:
        
            # Insert it for each instance
            for num in range(remaining_units):
                sell_queue.insert(index, average_price)
            
            return

    # If we've cycled through the entire list, and it's made it this far, we add it at the end
    for num in range(remaining_units):
        sell_queue.append(average_price)
    return          
    
  
def getPrice(client, symbol_pair_string):
    ticker = client.get_product_ticker(product_id=symbol_pair_string)
    
    return float(ticker['price'])

def calculateStocasticOscillator():


    current_position = len(list_of_prices_for_averages)
    sub_list = list_of_prices_for_averages[(current_position - k_window):current_position]
    #print(sub_list)
    
    percent_k = _calculatePercentK(sub_list)
    
    sum_of_previous_percent_ks = 0
    
    for i in range(d_window):
        sub_list = list_of_prices_for_averages[((len(list_of_prices_for_averages) - k_window) - i):(len(list_of_prices_for_averages) - i)]
        sum_of_previous_percent_ks += _calculatePercentK(sub_list)
        
    percent_n = float(sum_of_previous_percent_ks / d_window)
    
    return percent_k, percent_n


    
def _calculatePercentK(list):
    
    global previous_percent_k
    
    low = list[0]
    high = list[0]
    
    for item in list:
        
        if item < low:
            low = item
            
        if item > high:
            high = item
            
    most_recent_price = list[-1]
    second_most_recent_price = list[-2]
    
    # If its within the tolerance, I don't want it to swing too much. It'll just return the previous %K
    if (most_recent_price <= (second_most_recent_price + percent_k_price_tolerance)) \
        and (most_recent_price >= (second_most_recent_price - percent_k_price_tolerance)):
        return previous_percent_k
    
    # Not sure about this, but worth a shot
    # This is to prevent divide by 0 issues
    if high == low:
        if most_recent_price > low:
            previous_percent_k = 1
            return 1
        else:
            previous_percent_k = 0
            return 0

    percent_k = float(100.0 * (most_recent_price - low) / (high - low))
    previous_percent_k = percent_k
    return percent_k
    
    
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--pair", help="Currency Pair for Trading (Examples: LTC-USD, BTC-USD, ETH-USD)", action="store", required=True)
    parser.add_argument("-k", "--percentk", help="Sampling Rate for %K", action="store", type=int)
    parser.add_argument("-d", "--percentd", help="Sampling Rate for %D", action="store", type=int)
    parser.add_argument("-n", "--percentdn", help="Sampling Rate for %Dn", action="store", type=int)
    parser.add_argument("-i", "--interval", help="Interval between polling between ms (minimum is .2)", action="store", type=float)
    parser.add_argument("-a", "--amount", help="Amount you want to trade (BTC minimum is .001, ETH minimum is .01, LTC minimum is .1)", action="store", type=float, required=True)
    args = parser.parse_args()

    pair = args.pair
    k = args.percentk
    d = args.percentd
    dn = args.percentdn
    interval = args.interval
    amount = args.amount
    
    # Use default values if not defined:
    if not k:
        k = k_window
    if not d:
        d = d_window
    if not dn:
        dn = d_n_window
    
    print("Currency Pair: {}".format(pair))
    print("Trade Amounts: {}".format(amount))
    print("Poll Interval: {}sec".format(interval))
    print("%k: {}".format(k))
    print("%d: {}".format(d))
    print("%Dn: {}".format(dn))
    
    main(pair, k, d, dn, interval, amount)
