/**
 * Alarm Acknowledgement Form
 * Wraps SignatureModal for alarm-specific acknowledgement.
 * DANGER/HIGH_DOSE alarms require electronic signature (re-authentication).
 * All alarms require a minimum 10-character comment.
 */
import React from 'react';
import { Alarm } from '../../types/alarms';
import { SignatureModal } from '../common/SignatureModal';
import { useAuthStore } from '../../store/authStore';
import api from '../../services/api';

interface Props {
  alarm: Alarm;
  onClose: () => void;
  onAcknowledged: () => void;
}

export const AcknowledgeForm: React.FC<Props> = ({ alarm, onClose, onAcknowledged }) => {
  const { user } = useAuthStore();
  const showSig = true;

  const handleConfirm = async (password: string, comment?: string) => {
    await api.post(`/alarms/${alarm.alarm_id}/acknowledge`, {
      comment: comment || '',
      signature_password: password,
      meaning: `I acknowledge alarm ${alarm.alarm_id} on channel ${alarm.channel_code} and confirm I have reviewed the associated data.`,
    });
    onAcknowledged();
    onClose();
  };

  return (
    <SignatureModal
      isOpen={showSig}
      title={`Acknowledge ${alarm.severity_level} Alarm`}
      meaning={`I acknowledge the ${alarm.severity_level} alarm on ${alarm.channel_code}: "${alarm.alarm_message}". I confirm I have assessed the situation and taken appropriate action.`}
      username={user?.username || ''}
      onConfirm={handleConfirm}
      onCancel={onClose}
      requireComment={true}
    />
  );
};
