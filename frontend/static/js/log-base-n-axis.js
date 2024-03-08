import { Scale } from 'chart.umd.js';
import zoomPlugin from 'chartjs-plugin-zoom.min.js';


// define new logarithmic scale based on this exponent
class LogBaseAxis extends Scale {
    constructor(cfg) {
        super(cfg);
        this._startValue = undefined;
        this._valueRange = 0;
    }

    parse(raw, index) {
        const value = Chart.LinearScale.prototype.parse.apply(this, [raw, index]);
        return isFinite(value) && value > 0 ? value : null;
    }

    determineDataLimits() {
        const {
            min,
            max
        } = this.getMinMax(true);
        this.min = isFinite(min) ? Math.max(0, min) : null;
        this.max = isFinite(max) ? Math.max(0, max) : null;

        this.handleTickRangeOptions();
    }

    handleTickRangeOptions() {
        const { minDefined, maxDefined } = this.getUserBounds();
        let min = this.min;
        let max = this.max;

        const setMin = v => (min = minDefined ? min : v);
        const setMax = v => (max = maxDefined ? max : v);

        if (min === max) {
            if (min <= 0) { // includes null
                setMin(1);
                setMax(3);
            } else {
                setMin(changeExponent(min, -1));
                setMax(changeExponent(max, +1));
            }
        }
        if (min <= 0) {
            setMin(changeExponent(max, -1));
        }
        if (max <= 0) {
            setMax(changeExponent(min, +1));
        }

        this.min = min;
        this.max = max;
    }

    buildTicks() {
        const ticks = [];
        if (this.min > this.max) {
            let temp = this.min;
            this.min = this.max;
            this.max = temp;
        }
        let exponent = rcParam[0].exp;
        let minPowerData = Math.log((this.min)) / Math.log(exponent);
        let maxPowerData = Math.log((this.max)) / Math.log(exponent);

        if (minPowerData > maxPowerData) {
            minPowerData = -minPowerData;
            maxPowerData = -maxPowerData;
        }

        let minPower = Math.floor(minPowerData);
        let maxPower = Math.ceil(maxPowerData);

        let numTicks = maxPower - minPower + 1;
        let powerStep = (maxPower - minPower) / 10;

        // iteratively find lowest power to plot a tick for
        let power = maxPower;
        while ((power > minPower) && (power >= minPowerData)) {
            power -= powerStep;
        }
        // add ticks from smallest to largest
        while (power <= (maxPower + powerStep)) {
            let tickVal = Math.pow(exponent, power);

            // if exponent is less than 1, take negative
            if (exponent < 1) {
                tickVal = Math.pow(exponent, -power);
            }

            // adjust to use rounded tick value based on log10 of value
            let roundMag = -Math.floor(Math.log10(tickVal));
            let tickValRound = Math.round(tickVal * 10 ** (roundMag + 2)) / 10 ** (roundMag + 2);

            ticks.push({
                value: tickValRound
            });

            power += powerStep;
        }

        try {
            this.min = ticks[0].value;
            this.max = ticks[ticks.length - 1].value;
        } catch (e) {
            // show temporary ticks:
            this.min = 0;
            this.max = 1;

            // display warning/error message on top
            updateWarningMessage(
                { 'error_title': 'Error', 'error_text': 'No ticks found for logarithmic scale! Please adjust the exponent of the rating curve by changing your endpoints or triggering the autofit again!' },
                { 'title': 'none', 'url': 'none' }
            );

            // force non-log scale:
            document.getElementById("toggle_axis_format").checked = false;
        }
        return ticks;
    }

    /**
        * @protected
        */
    configure() {
        const start = this.min;

        super.configure();

        this._startValue = Math.log(start) / Math.log(rcParam[0].exp);
        this._valueRange = Math.log(this.max) / Math.log(rcParam[0].exp) - Math.log(start) / Math.log(rcParam[0].exp);
    }

    getPixelForValue(value) {
        if (value === undefined || value === 0) {
            value = this.min;
        }
        if (value === null || isNaN(value)) {
            return NaN;
        }

        return this.getPixelForDecimal(value === this.min ? 0 :
            (Math.log(value) / Math.log(rcParam[0].exp) - this._startValue) / this._valueRange);
    }

    getValueForPixel(pixel) {
        const decimal = this.getDecimalForPixel(pixel);
        return Math.pow(rcParam[0].exp, this._startValue + decimal * this._valueRange);
    }
}