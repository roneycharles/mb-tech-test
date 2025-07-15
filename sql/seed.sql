-- Insert ETH:
INSERT INTO tokens (name, symbol, address, decimals, type, is_active)
VALUES ('Ether', 'ETH', lower('1'), 18, 'MAINCOIN', true);

-- Insert USDC:
INSERT INTO tokens (name, symbol, address, decimals, type, is_active)
VALUES ('USD Coin', 'USDC', LOWER('0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238'), 6, 'ERC20', true);

-- Insert address with valid ETH and USDC balance
-- Address: 0xf1f7f5b16c02563cd2c981edbd8921153a846247
-- To get more ETH balance on SEPOLIA Network: https://sepolia-faucet.pk910.de/#/
INSERT INTO addresses (
    address,
    private_key,
    is_active
) VALUES (
    '0xf1f7f5b16c02563cd2c981edbd8921153a846247',
    'gAAAAABodbUVoXcWzqpdBEuaQF_dY_5RX-LRpWzkwNOsOAhvsTdsSIB71ywJQ36Nq__FlNrHe07EVkNe4iKdLMmAL5NkKMhN3f_abIJyI34as2_hZuV8Q-59zpznohanWSmL1JXbzcWEHsWQH9iTrCAP6uShbMMdbY5P-dsmAUMriiODBv-0v_M=',
    true
);