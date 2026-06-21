import { useState } from "react";
import { useSignAndExecuteTransaction, useSuiClient } from "@mysten/dapp-kit";
import { Transaction } from "@mysten/sui/transactions";
import { useSuiWallet } from "./useSuiWallet";
import { CONTRACTS, suiToMist } from "@/lib/contracts";
import { buildRegisterVoiceArguments } from "@/lib/voiceContract";
import { toast } from "sonner";

export interface VoiceRegistrationData {
  name: string;
  modelUri: string;
  rights: string;
  pricePerUse: number; // in SUI
}

export function useVoiceRegister() {
  const { isConnected, address } = useSuiWallet();
  const suiClient = useSuiClient();
  const { mutateAsync: signAndExecute } = useSignAndExecuteTransaction();
  const [isRegistering, setIsRegistering] = useState(false);

  const registerVoice = async (data: VoiceRegistrationData) => {
    if (!isConnected || !address) {
      toast.error("Please connect your wallet first");
      return null;
    }

    setIsRegistering(true);

    try {
      const priceInMist = suiToMist(data.pricePerUse);

      const tx = new Transaction();
      const registerArgs = await buildRegisterVoiceArguments(suiClient, tx, {
        name: data.name,
        modelUri: data.modelUri,
        rights: data.rights,
        priceInMist,
      });

      // Supports both deployed contract shapes: register_voice(...) and register_voice(registry, ...).
      const voice = tx.moveCall({
        target: `${CONTRACTS.PACKAGE_ID}::${CONTRACTS.VOICE_IDENTITY.module}::register_voice`,
        arguments: registerArgs,
      });

      // Transfer the returned VoiceIdentity object to the sender
      tx.transferObjects([voice], address);

      toast.info("Please approve the transaction in your wallet...");

      const result = await signAndExecute({
        transaction: tx,
      });

      const txDigest = result.digest;

      toast.info("Waiting for transaction confirmation...");

      try {
        await suiClient.waitForTransaction({
          digest: txDigest,
        });

        toast.success("Voice registered on-chain successfully!", {
          description: `Transaction confirmed: ${txDigest.slice(0, 8)}...${txDigest.slice(-6)}`,
        });

        return {
          success: true,
          transactionHash: txDigest,
        };
      } catch (waitError: any) {
        console.warn("Transaction wait timeout, but transaction was submitted:", waitError);
        toast.success("Transaction submitted! Waiting for confirmation...", {
          description: `TX: ${txDigest.slice(0, 8)}...${txDigest.slice(-6)}`,
        });

        return {
          success: true,
          transactionHash: txDigest,
        };
      }
    } catch (error: any) {
      console.error("Voice registration error:", error);

      let errorMessage = error.message || "Unknown error occurred";

      if (errorMessage.includes("user rejected") || errorMessage.includes("User rejected")) {
        errorMessage = "Transaction was rejected by user";
      } else if (errorMessage.includes("insufficient") || errorMessage.includes("No valid gas")) {
        errorMessage = "Insufficient balance. Please ensure you have enough SUI to cover transaction fees.";
      }

      toast.error("Registration failed", {
        description: errorMessage,
        duration: 7000,
      });
      return null;
    } finally {
      setIsRegistering(false);
    }
  };

  return {
    registerVoice,
    isRegistering,
  };
}
