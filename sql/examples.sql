-- Quality: Top scrap reasons by quantity
SELECT
    sr.Name AS ScrapReason,
    SUM(wo.ScrappedQty) AS TotalScrapped,
    COUNT(wo.WorkOrderID) AS WorkOrders
FROM Production.WorkOrder wo
JOIN Production.ScrapReason sr
    ON wo.ScrapReasonID = sr.ScrapReasonID
WHERE wo.ScrappedQty > 0
GROUP BY sr.Name
ORDER BY TotalScrapped DESC;

-- Inventory: Stock levels by product and location
SELECT
    p.Name AS ProductName,
    l.Name AS LocationName,
    pi.Quantity AS StockOnHand,
    pi.Shelf,
    pi.Bin
FROM Production.ProductInventory pi
JOIN Production.Product p
    ON pi.ProductID = p.ProductID
JOIN Production.Location l
    ON pi.LocationID = l.LocationID
ORDER BY pi.Quantity DESC;

--Logistics: Vendor lead times and order costs
SELECT
    v.Name AS VendorName,
    v.CreditRating,
    pv.AverageLeadTime,
    pv.StandardPrice,
    pv.MinOrderQty,
    pv.MaxOrderQty
FROM Purchasing.Vendor v
JOIN Purchasing.ProductVendor pv
    ON v.BusinessEntityID = pv.BusinessEntityID
ORDER BY pv.AverageLeadTime ASC;

--TQM: Supplier scorecard (rejected vs received)
SELECT
    v.Name AS VendorName,
    v.CreditRating,
    SUM(pod.OrderQty) AS TotalOrdered,
    SUM(pod.ReceivedQty) AS TotalReceived,
    SUM(pod.RejectedQty) AS TotalRejected,
    ROUND(SUM(pod.RejectedQty) * 100.0 / 
        NULLIF(SUM(pod.ReceivedQty), 0), 2) AS RejectionRatePct
FROM Purchasing.Vendor v
JOIN Purchasing.PurchaseOrderHeader poh
    ON v.BusinessEntityID = poh.VendorID
JOIN Purchasing.PurchaseOrderDetail pod
    ON poh.PurchaseOrderID = pod.PurchaseOrderID
GROUP BY v.Name, v.CreditRating
ORDER BY RejectionRatePct DESC;