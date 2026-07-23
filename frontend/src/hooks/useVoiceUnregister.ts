import { useState } from "react";
import { useSignAndExecuteTransaction, useSuiClient } from "@mysten/dapp-kit";
import { Transaction } from "@mysten/sui/transactions";
import { useSuiWallet } from "./useSuiWallet";
import { CONTRACTS } from "@/lib/contracts";
import { assertOwnedVoiceObject, buildDeleteVoiceArguments } from "@/lib/voiceContract";
import { toast } from "sonner";

export function useVoiceUnregister() {
  const { isConnected, address } = useSuiWallet();
  const suiClient = useSuiClient();
  const { mutateAsync: signAndExecute } = useSignAndExecuteTransaction();
  const [isUnregistering, setIsUnregistering] = useState(false);

  /**
   * Delete a VoiceIdentity object owned by the current user.
   * @param voiceObjectId The object ID of the VoiceIdentity to delete
   */
  const unregisterVoice = async (voiceObjectId: string) => {
    if (!isConnected || !address) {
      toast.error("Please connect your wallet first");
      return null;
    }

    if (!voiceObjectId) {
      toast.error("No voice object ID provided");
      return null;
    }

    setIsUnregistering(true);

    try {
      await assertOwnedVoiceObject(suiClient, voiceObjectId, address);

      const tx = new Transaction();
      const deleteArgs = await buildDeleteVoiceArguments(suiClient, tx, voiceObjectId);

      tx.moveCall({
        target: `${CONTRACTS.PACKAGE_ID}::${CONTRACTS.VOICE_IDENTITY.module}::delete_voice`,
        arguments: deleteArgs,
      });

      toast.info("Please approve the transaction in your wallet...");

      const result = await signAndExecute({
        transaction: tx,
      });

      const txDigest = result.digest;

      toast.info("Waiting for transaction confirmation...");

      try {
        await suiClient.waitForTransaction({ digest: txDigest });

        toast.success("Voice deleted on-chain successfully!", {
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
      console.error("Voice unregistration error:", error);

      let errorMessage = error.message || "Unknown error occurred";

      if (errorMessage.includes("user rejected") || errorMessage.includes("User rejected")) {
        errorMessage = "Transaction was rejected by user";
      } else if (errorMessage.includes("insufficient") || errorMessage.includes("No valid gas")) {
        errorMessage = "Insufficient balance. Please ensure you have enough SUI to cover transaction fees.";
      }

      toast.error("Deletion failed", {
        description: errorMessage,
        duration: 7000,
      });
      return null;
    } finally {
      setIsUnregistering(false);
    }
  };

  return {
    unregisterVoice,
    isUnregistering,
  };
}
