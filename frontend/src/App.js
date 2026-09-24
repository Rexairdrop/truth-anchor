import React, { useEffect, useState } from 'react';
import { createClient } from 'genlayer-js';
import { testnetBradbury } from 'genlayer-js/chains';
import './App.css';

const CONTRACT_ADDRESS =
  process.env.REACT_APP_CONTRACT_ADDRESS ||
  '0x98dbA630c1D6D0e039216b44A0669A3DeB341883';

function App() {
  const [account, setAccount] = useState(null);
  const [genlayerClient, setGenlayerClient] = useState(null);

  const [flightKey, setFlightKey] = useState('');
  const [airline, setAirline] = useState('');
  const [flightNum, setFlightNum] = useState('');
  const [depDate, setDepDate] = useState('');

  const [txState, setTxState] = useState('IDLE');
  const [errorMessage, setErrorMessage] = useState('');
  const [policyStatus, setPolicyStatus] = useState(null);
  const [txHash, setTxHash] = useState('');

  /*
   * CONNECT WALLET
   */
  
const connectWallet = async () => {
  setTxState('CONNECTING');
  setErrorMessage('');

  try {
    if (!window.ethereum) {
      throw new Error(
        'No browser wallet detected. Please install or enable your wallet extension.'
      );
    }

    // 1. Ask the wallet for the user's account.
    const accounts = await window.ethereum.request({
      method: 'eth_requestAccounts',
    });

    if (!accounts || accounts.length === 0) {
      throw new Error('No wallet account was returned.');
    }

    const walletAddress = accounts[0];

    console.log('Wallet account:', walletAddress);

    // 2. Check the current wallet network.
    const currentChainId = await window.ethereum.request({
      method: 'eth_chainId',
    });

    console.log('Current wallet chain:', currentChainId);

    // Bradbury = 4221 = 0x107d
    const BRADBURY_CHAIN_ID = '0x107d';

    // 3. Switch to GenLayer Bradbury if necessary.
    if (currentChainId.toLowerCase() !== BRADBURY_CHAIN_ID) {
      try {
        await window.ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [
            {
              chainId: BRADBURY_CHAIN_ID,
            },
          ],
        });
      } catch (switchError) {
        console.error('Wallet network switch error:', switchError);

        if (switchError?.code === 4902) {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [
              {
                chainId: BRADBURY_CHAIN_ID,
                chainName: 'GenLayer Bradbury Testnet',
                nativeCurrency: {
                  name: 'GEN',
                  symbol: 'GEN',
                  decimals: 18,
                },
                rpcUrls: [
                  'https://rpc-bradbury.genlayer.com',
                ],
                blockExplorerUrls: [
                  'https://explorer-bradbury.genlayer.com/',
                ],
              },
            ],
          });
        } else {
          throw switchError;
        }
      }
    }

    // 4. Verify that the wallet actually switched.
    const verifiedChainId = await window.ethereum.request({
      method: 'eth_chainId',
    });

    console.log('Verified wallet chain:', verifiedChainId);

    if (verifiedChainId.toLowerCase() !== BRADBURY_CHAIN_ID) {
      throw new Error(
        `Wallet is still on chain ${verifiedChainId}. Bradbury requires chain 4221.`
      );
    }

    // 5. Create the GenLayer client.
    //
    // IMPORTANT:
    // Do NOT call genlayerClient.connect() here.
    // That SDK path is what is triggering wallet_getSnaps in your setup.
    const client = createClient({
      chain: testnetBradbury,
      account: walletAddress,
      provider: window.ethereum,
    });

    // 6. Store the connected wallet/client in React state.
    setAccount(walletAddress);
    setGenlayerClient(client);

    // We don't actually need ethers for GenLayerJS writes.
    setProvider(null);
    setSigner(null);

    setTxState('IDLE');

    console.log('GenLayer client ready.');
    console.log('Connected account:', walletAddress);
    console.log('Connected chain: Bradbury / 4221');
  } catch (err) {
    console.error('WALLET CONNECTION ERROR:', err);

    setTxState('ERROR');

    setErrorMessage(
      err?.message ||
        err?.shortMessage ||
        'Failed to connect wallet.'
    );
  }
};

  /*
   * READ POLICY STATE
   */
  const checkPolicyState = async (
    userAddress = account,
    key = flightKey
  ) => {
    if (!genlayerClient || !userAddress || !key) {
      return;
    }

    try {
      const state = await genlayerClient.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_policy_state',
        args: [userAddress, key],
      });

      console.log('Policy state:', state);

      setPolicyStatus(String(state));
    } catch (err) {
      console.error('POLICY READ ERROR:', err);
    }
  };

  /*
   * PURCHASE INSURANCE
   *
   * IMPORTANT:
   * We are deliberately NOT calling:
   *
   * estimateTransactionFeesForWrite()
   *
   * because that method is not available on the installed
   * genlayer-js@1.1.8 client object.
   */
const purchaseInsurance = async () => {
  if (!genlayerClient) {
    setErrorMessage('Connect your wallet first.');
    return;
  }

  if (!flightKey) {
    setErrorMessage('Enter a flight key first.');
    return;
  }

  setTxState('SIGNING');
  setErrorMessage('');
  setTxHash('');

  try {
    const userValue = 10n ** 16n; // 0.01 GEN

    const write = {
      address: CONTRACT_ADDRESS,
      functionName: 'buy_policy',
      args: [flightKey],
      value: userValue,
    };

    console.log('Submitting GenLayer purchase:', write);

    /*
     * IMPORTANT:
     * Your installed genlayer-js is 1.1.8.
     * Do not use estimateTransactionFeesForWrite() here because
     * that method is not available in your installed SDK.
     *
     * We already know from your successful transaction that
     * writeContract() can submit this call.
     */
    const hash = await genlayerClient.writeContract(write);

    console.log('GenLayer transaction hash:', hash);

    setTxHash(hash);
    setTxState('SUBMITTED');

    /*
     * The transaction ID now exists.
     * Do NOT submit the purchase again if waiting fails.
     *
     * Instead, read the persisted transaction state.
     */
    let transaction;

    for (let attempt = 0; attempt < 60; attempt++) {
      transaction = await genlayerClient.getTransaction({
        hash,
      });

      console.log(
        `Transaction check ${attempt + 1}:`,
        transaction.statusName,
        '/',
        transaction.txExecutionResultName
      );

      /*
       * Successful execution:
       * ACCEPTED or FINALIZED
       * +
       * FINISHED_WITH_RETURN
       */
      if (
        (transaction.statusName === 'ACCEPTED' ||
          transaction.statusName === 'FINALIZED') &&
        transaction.txExecutionResultName === 'FINISHED_WITH_RETURN'
      ) {
        console.log('Purchase successfully accepted by GenLayer.');
        console.log('Transaction:', transaction);

        setTxState('FINALIZED');

        /*
         * Read the actual on-chain policy state after the
         * successful transaction.
         */
        await checkPolicyState(account, flightKey);

        return;
      }

      /*
       * These states represent an actual unsuccessful outcome.
       */
      if (
        transaction.statusName === 'CANCELED' ||
        transaction.statusName === 'UNDETERMINED'
      ) {
        throw new Error(
          `Transaction did not reach successful consensus: ${transaction.statusName}`
        );
      }

      if (
        transaction.txExecutionResultName === 'FINISHED_WITH_ERROR'
      ) {
        throw new Error(
          `Contract execution failed: ${transaction.txExecutionResultName}`
        );
      }

      /*
       * Transaction is still progressing.
       */
      await new Promise((resolve) => setTimeout(resolve, 5000));
    }

    throw new Error(
      'Transaction is still processing. Keep the transaction hash and check it again instead of submitting another purchase.'
    );
  } catch (err) {
    console.error('PURCHASE ERROR:', err);

    setTxState('ERROR');

    setErrorMessage(
      err?.message ||
        err?.shortMessage ||
        'Insurance purchase failed.'
    );
  }
};

  /*
   * CLAIM PAYOUT
   */
  const triggerConsensusClaim = async () => {
    if (!genlayerClient) {
      setErrorMessage('Connect your wallet first.');
      return;
    }

    if (
      !flightKey.trim() ||
      !airline.trim() ||
      !flightNum.trim() ||
      !depDate.trim()
    ) {
      setErrorMessage(
        'Fill in the flight key, airline, flight number and departure date.'
      );
      return;
    }

    setTxState('PENDING');
    setErrorMessage('');
    setTxHash('');

    try {
      const write = {
        address: CONTRACT_ADDRESS,
        functionName: 'claim_payout',
        args: [
          flightKey.trim(),
          airline.trim(),
          flightNum.trim(),
          depDate.trim(),
        ],
      };

      console.log('GenLayer claim request:', write);

      /*
       * Submit the consensus transaction.
       */
      const hash = await genlayerClient.writeContract(write);

      console.log('Claim transaction hash:', hash);

      setTxHash(hash);
      setTxState('SUBMITTED');

      /*
       * Wait until finalized.
       */
      const receipt =
        await genlayerClient.waitForTransactionReceipt({
          hash,
          waitUntil: 'finalized',
        });

      console.log('Claim receipt:', receipt);

      const statusName = receipt?.statusName;
      const executionResult =
        receipt?.txExecutionResultName;

      if (
        (statusName === 'ACCEPTED' ||
          statusName === 'FINALIZED') &&
        executionResult === 'FINISHED_WITH_RETURN'
      ) {
        setTxState('FINALIZED');

        await checkPolicyState(
          account,
          flightKey.trim()
        );
      } else {
        throw new Error(
          `Claim failed: ${statusName || 'UNKNOWN'} / ${
            executionResult || 'UNKNOWN'
          }`
        );
      }
    } catch (err) {
      console.error('CLAIM ERROR:', err);

      setTxState('ERROR');

      setErrorMessage(
        err?.shortMessage ||
          err?.message ||
          String(err)
      );
    }
  };

  /*
   * ACCOUNT / NETWORK EVENTS
   */
  useEffect(() => {
    if (!window.ethereum) {
      return undefined;
    }

    const handleAccountsChanged = (accounts) => {
      if (!accounts || accounts.length === 0) {
        setAccount(null);
        setGenlayerClient(null);
        setPolicyStatus(null);
        setTxState('IDLE');
        return;
      }

      setAccount(accounts[0]);
    };

    const handleChainChanged = () => {
      /*
       * Recreate the provider/client against the new chain.
       */
      window.location.reload();
    };

    window.ethereum.on(
      'accountsChanged',
      handleAccountsChanged
    );

    window.ethereum.on(
      'chainChanged',
      handleChainChanged
    );

    return () => {
      window.ethereum.removeListener(
        'accountsChanged',
        handleAccountsChanged
      );

      window.ethereum.removeListener(
        'chainChanged',
        handleChainChanged
      );
    };
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>TruthAnchor Insurance</h1>

        {account ? (
          <span className="wallet-badge connected">
            Connected: {account.slice(0, 6)}...
            {account.slice(-4)}
          </span>
        ) : (
          <button
            className="connect-btn"
            onClick={connectWallet}
          >
            Connect Real Wallet
          </button>
        )}
      </header>

      <main className="app-content">
        <section className="form-card">
          <h2>1. Purchase Active Coverage</h2>

          <input
            type="text"
            placeholder="Unique Flight Key (e.g. AA100-20260910)"
            value={flightKey}
            onChange={(e) =>
              setFlightKey(e.target.value)
            }
          />

          <button
            disabled={
              !account ||
              !genlayerClient ||
              txState === 'SIGNING' ||
              txState === 'SUBMITTED'
            }
            onClick={purchaseInsurance}
          >
            Sign & Pay 0.01 GEN Premium
          </button>
        </section>

        <section className="form-card">
          <h2>2. Process On-Chain Consensus Claim</h2>

          <input
            type="text"
            placeholder="Airline (e.g. AA)"
            value={airline}
            onChange={(e) =>
              setAirline(e.target.value)
            }
          />

          <input
            type="text"
            placeholder="Flight Number (e.g. 100)"
            value={flightNum}
            onChange={(e) =>
              setFlightNum(e.target.value)
            }
          />

          <input
            type="text"
            placeholder="Departure Date (YYYY-MM-DD)"
            value={depDate}
            onChange={(e) =>
              setDepDate(e.target.value)
            }
          />

          <button
            disabled={
              !account ||
              !genlayerClient ||
              txState === 'PENDING' ||
              txState === 'SUBMITTED'
            }
            onClick={triggerConsensusClaim}
          >
            Execute Decentralized Payout Check
          </button>
        </section>

        <section className="status-terminal">
          <h3>Live Operational Terminal</h3>

          <div
            className={`status-banner state-${txState}`}
          >
            Current State:{' '}
            <strong>{txState}</strong>
          </div>

          {txHash && (
            <div className="status-data">
              Transaction:
              <br />
              {txHash}
            </div>
          )}

          {policyStatus !== null && (
            <div className="status-data">
              On-Chain Policy Flag:{' '}
              {policyStatus === '0'
                ? 'Active'
                : policyStatus === '1'
                ? 'Paid Out (Delayed)'
                : 'Rejected (On-Time)'}
            </div>
          )}

          {errorMessage && (
            <div className="error-box">
              🛑 Operational Error: {errorMessage}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;