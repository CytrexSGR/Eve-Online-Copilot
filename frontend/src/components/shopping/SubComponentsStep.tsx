import { useState, useCallback } from 'react';
import { ArrowLeft, ArrowRight, Loader2, ShoppingCart, Wrench } from 'lucide-react';
import { api } from '../../api';
import { formatQuantity } from '../../utils/format';
import type {
  ProductInfo,
  SubComponent,
  Decisions,
  Decision,
  ShoppingItem,
  ShoppingTotals,
  CalculateMaterialsResponse,
} from './types';

interface SubComponentsStepProps {
  product: ProductInfo;
  subComponents: SubComponent[];
  decisions: Decisions;
  onDecisionsUpdated: (
    decisions: Decisions,
    shoppingList: ShoppingItem[],
    totals: ShoppingTotals
  ) => void;
  onProceed: () => void;
  onBack: () => void;
}

interface ToggleButtonProps {
  value: Decision;
  onChange: (value: Decision) => void;
  disabled?: boolean;
}

function ToggleButton({ value, onChange, disabled }: ToggleButtonProps) {
  return (
    <div style={{
      display: 'flex',
      background: 'var(--bg-darker)',
      borderRadius: 6,
      padding: 2,
    }}>
      <button
        onClick={() => onChange('buy')}
        disabled={disabled}
        style={{
          padding: '6px 12px',
          borderRadius: 4,
          border: 'none',
          background: value === 'buy' ? 'var(--accent-blue)' : 'transparent',
          color: value === 'buy' ? 'white' : 'var(--text-secondary)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          fontSize: 13,
          fontWeight: 500,
        }}
      >
        <ShoppingCart size={14} />
        BUY
      </button>
      <button
        onClick={() => onChange('build')}
        disabled={disabled}
        style={{
          padding: '6px 12px',
          borderRadius: 4,
          border: 'none',
          background: value === 'build' ? 'var(--accent-green)' : 'transparent',
          color: value === 'build' ? 'white' : 'var(--text-secondary)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          fontSize: 13,
          fontWeight: 500,
        }}
      >
        <Wrench size={14} />
        BUILD
      </button>
    </div>
  );
}

export function SubComponentsStep({
  product,
  subComponents,
  decisions,
  onDecisionsUpdated,
  onProceed,
  onBack,
}: SubComponentsStepProps) {
  const [localDecisions, setLocalDecisions] = useState<Decisions>(decisions);
  const [isRecalculating, setIsRecalculating] = useState(false);

  const recalculateMaterials = useCallback(async (newDecisions: Decisions) => {
    setIsRecalculating(true);

    try {
      const response = await api.post<CalculateMaterialsResponse>('/api/shopping/wizard/calculate-materials', {
        product_type_id: product.type_id,
        runs: product.runs,
        me_level: product.me_level,
        decisions: newDecisions,
      });

      onDecisionsUpdated(
        newDecisions,
        response.data.shopping_list || [],
        response.data.totals as ShoppingTotals
      );
    } catch (err) {
      console.error('Failed to recalculate materials:', err);
    }

    setIsRecalculating(false);
  }, [product, onDecisionsUpdated]);

  const handleDecisionChange = useCallback((typeId: number, decision: Decision) => {
    const newDecisions = {
      ...localDecisions,
      [typeId.toString()]: decision,
    };
    setLocalDecisions(newDecisions);
    recalculateMaterials(newDecisions);
  }, [localDecisions, recalculateMaterials]);

  const handleSelectAll = useCallback((decision: Decision) => {
    const newDecisions: Decisions = {};
    subComponents.forEach(sc => {
      newDecisions[sc.type_id.toString()] = decision;
    });
    setLocalDecisions(newDecisions);
    recalculateMaterials(newDecisions);
  }, [subComponents, recalculateMaterials]);

  const buildCount = Object.values(localDecisions).filter(d => d === 'build').length;
  const buyCount = Object.values(localDecisions).filter(d => d === 'buy').length;

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 8 }}>Step 2: Sub-Components</h2>
      <p className="neutral" style={{ marginBottom: 8 }}>
        Building: <strong>{product.runs}x {product.name}</strong>
      </p>
      <p className="neutral" style={{ marginBottom: 24 }}>
        Choose whether to buy each sub-component from the market or build it yourself.
      </p>

      {/* Select All Buttons */}
      <div style={{
        display: 'flex',
        gap: 12,
        marginBottom: 16,
        padding: 16,
        background: 'var(--bg-dark)',
        borderRadius: 8,
      }}>
        <span style={{ fontWeight: 500, marginRight: 8 }}>Select All:</span>
        <button
          onClick={() => handleSelectAll('buy')}
          disabled={isRecalculating}
          className="btn btn-secondary"
          style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <ShoppingCart size={16} />
          BUY ALL
        </button>
        <button
          onClick={() => handleSelectAll('build')}
          disabled={isRecalculating}
          className="btn btn-secondary"
          style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <Wrench size={16} />
          BUILD ALL
        </button>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16 }}>
          <span className="neutral">
            <ShoppingCart size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
            {buyCount} to buy
          </span>
          <span className="neutral">
            <Wrench size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
            {buildCount} to build
          </span>
        </div>
      </div>

      {/* Sub-Components List */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        marginBottom: 24,
        maxHeight: 400,
        overflow: 'auto',
      }}>
        {subComponents.map((component) => {
          const decision = localDecisions[component.type_id.toString()] || 'buy';

          return (
            <div
              key={component.type_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                background: 'var(--bg-dark)',
                borderRadius: 8,
                borderLeft: `3px solid ${decision === 'build' ? 'var(--accent-green)' : 'var(--accent-blue)'}`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div>
                  <div style={{ fontWeight: 500 }}>{component.item_name}</div>
                  <div className="neutral" style={{ fontSize: 12 }}>
                    Quantity: {formatQuantity(component.quantity)}
                  </div>
                </div>
              </div>

              <ToggleButton
                value={decision}
                onChange={(value) => handleDecisionChange(component.type_id, value)}
                disabled={isRecalculating}
              />
            </div>
          );
        })}
      </div>

      {/* Loading Indicator */}
      {isRecalculating && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginBottom: 16,
          color: 'var(--text-secondary)',
        }}>
          <Loader2 size={16} className="spin" />
          Recalculating materials...
        </div>
      )}

      {/* Navigation Buttons */}
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <button
          onClick={onBack}
          className="btn btn-secondary"
          style={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <ArrowLeft size={18} />
          Back
        </button>

        <button
          onClick={onProceed}
          disabled={isRecalculating}
          className="btn btn-primary"
          style={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 8 }}
        >
          Next Step
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}

export default SubComponentsStep;
