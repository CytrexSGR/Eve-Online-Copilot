# Bug: Shopping Region Selection - Wrong Row Selected

**Datum:** 2025-12-07
**Status:** Offen
**Komponente:** `frontend/src/pages/ShoppingPlanner.tsx`

---

## Problem

In der "Compare Regions" Ansicht im Shopping Planner:
- Beim Klicken auf eine Zelle zum Auswählen einer Region wird **manchmal die Zeile darunter** selected
- Beim zweiten Klick wird dann das richtige Item selected
- Das Verhalten ist inkonsistent und schwer reproduzierbar

## Vermutete Ursache

Die Query-Invalidierung im `onSuccess` der `updateItemRegion` Mutation (Zeile 631-634) löst ein Re-Render der Tabelle aus. Wenn die Daten zurückkommen und die Tabelle neu gerendert wird, kann sich die Zeile unter dem Cursor verschieben.

```typescript
// Zeile 624-635
const updateItemRegion = useMutation({
  mutationFn: async ({ itemId, region, price }) => {
    await api.patch(`/api/shopping/items/${itemId}/region`, null, {
      params: { region, price }
    });
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
    queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
  },
});
```

## Bereits versucht

1. `e.stopPropagation()` hinzugefügt (Zeile 1079)
2. `isPending` Check hinzugefügt um Doppelklicks zu verhindern (Zeile 1081)

Diese Fixes haben das Problem nicht gelöst.

## Mögliche Lösungen

### Option 1: Optimistic Updates
Statt Query zu invalidieren, das lokale Cache-Objekt direkt updaten:

```typescript
const updateItemRegion = useMutation({
  mutationFn: async ({ itemId, region, price }) => {
    await api.patch(`/api/shopping/items/${itemId}/region`, null, {
      params: { region, price }
    });
    return { itemId, region, price };
  },
  onMutate: async ({ itemId, region, price }) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: ['shopping-comparison', selectedListId] });

    // Snapshot previous value
    const previousComparison = queryClient.getQueryData(['shopping-comparison', selectedListId]);

    // Optimistically update
    queryClient.setQueryData(['shopping-comparison', selectedListId], (old: RegionalComparison) => ({
      ...old,
      items: old.items.map(item =>
        item.id === itemId
          ? { ...item, current_region: region, current_price: price }
          : item
      )
    }));

    return { previousComparison };
  },
  onError: (err, variables, context) => {
    // Rollback on error
    queryClient.setQueryData(['shopping-comparison', selectedListId], context?.previousComparison);
  },
  onSettled: () => {
    // Refetch after mutation settles (success or error)
    queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
  },
});
```

### Option 2: Debounce/Delay auf Invalidierung
```typescript
onSuccess: () => {
  setTimeout(() => {
    queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
  }, 100);
},
```

### Option 3: Stable Keys für Table Rows
Sicherstellen dass `key={item.id}` wirklich unique und stabil ist.

## Zum Debuggen

1. Chrome DevTools MCP wurde hinzugefügt: `claude mcp add chrome-devtools npx chrome-devtools-mcp@latest`
2. Chrome mit Remote Debugging starten: `google-chrome --remote-debugging-port=9222`
3. Session neu starten damit MCP geladen wird
4. Dann kann Claude direkt im Browser debuggen

## Betroffene Dateien

- `frontend/src/pages/ShoppingPlanner.tsx` (Zeilen 624-635, 1078-1091)
