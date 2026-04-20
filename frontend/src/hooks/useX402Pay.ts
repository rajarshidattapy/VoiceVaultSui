import { useState } from "react";
import { useSignAndExecuteTransaction, useSuiClient } from "@mysten/dapp-kit";
import { Transaction } from "@mysten/sui/transactions";
import { useSuiWallet } from "./useSuiWallet";
import { toast } from "sonner";

export interface X402PayOptions {
  voiceId: string;
  creatorAddress: string;
  /** Price in SUI (default 0.1) */
  priceSui?: number;
  /** Uses to unlock (default 2) */
  uses?: number;
}

export interface X402PayResult {
  txDigest: string;
  passId?: string;
  usesRemaining: number;
}

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const MIST_PER_SUI = 1_000_000_000;

export function useX402Pay() {
  const { isConnected, address } = useSuiWallet();
  const suiClient = useSuiClient();
  const { mutateAsync: signAndExecute } = useSignAndExecuteTransaction();
  const [isPaying, setIsPaying] = useState(false);

  const pay = async (opts: X402PayOptions): Promise<X402PayResult | null> => {
    if (!isConnected || !address) {
      toast.error("Connect your wallet first");
      return null;
    }

    const priceSui = opts.priceSui ?? 0.1;
    const uses = opts.uses ?? 2;
    const amountMist = Math.floor(priceSui * MIST_PER_SUI);

    setIsPaying(true);
    try {
      // Build a simple SUI transfer to the creator (royalty split handled off-chain for x402)
      const tx = new Transaction();
      const [coin] = tx.splitCoins(tx.gas, [tx.pure.u64(amountMist)]);
      tx.transferObjects([coin], tx.pure.address(opts.creatorAddress));

      toast.info(`Approving ${priceSui} SUI payment…`);
      const result = await signAndExecute({ transaction: tx });
      const txDigest = result.digest;

      // Wait for confirmation
      try { await suiClient.waitForTransaction({ digest: txDigest }); } catch { /* ok */ }

      // Register with backend → get UsagePass
      const resp = await fetch(`${API_URL}/api/x402/create-pass`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          txDigest,
          payer: address,
          voiceId: opts.voiceId,
          creator: opts.creatorAddress,
          amountMist,
          uses,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.reason || err.error || "Pass creation failed");
      }

      const json = await resp.json();
      const pass = json.pass as { id: string; uses_remaining: number };

      toast.success(`Access granted! ${pass.uses_remaining} uses remaining.`);
      return { txDigest, passId: pass.id, usesRemaining: pass.uses_remaining };
    } catch (err: any) {
      toast.error("Payment failed", { description: err.message });
      return null;
    } finally {
      setIsPaying(false);
    }
  };

  return { pay, isPaying };
}
