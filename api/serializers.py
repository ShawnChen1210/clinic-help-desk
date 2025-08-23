from rest_framework import serializers
from help_desk.models import *
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class UserSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSheet
        fields = '__all__'

class SheetColumnPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SheetColumnPreference
        fields = ['sheet_id', 'date_column', 'income_columns']


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = '__all__'

    def validate_tax_brackets(self, brackets, bracket_type):
        """Shared validation for both federal and provincial tax brackets"""
        if not isinstance(brackets, list):
            raise serializers.ValidationError(f"{bracket_type} tax brackets must be a list")

        for i, bracket in enumerate(brackets):
            if not isinstance(bracket, dict):
                raise serializers.ValidationError(f"Tax bracket {i + 1} must be a dictionary")

            # Check required fields
            required_fields = ['tax_rate', 'min_income', 'max_income']
            for field in required_fields:
                if field not in bracket or bracket[field] == '':
                    raise serializers.ValidationError(f"Tax bracket {i + 1} missing {field}")

                # Convert to float and validate
                try:
                    value = float(bracket[field])
                    if field == 'tax_rate' and (value < 0 or value > 100):
                        raise serializers.ValidationError(f"Tax bracket {i + 1} tax rate must be 0-100%")
                    elif field.endswith('income') and value < 0:
                        raise serializers.ValidationError(f"Tax bracket {i + 1} income cannot be negative")
                except (ValueError, TypeError):
                    raise serializers.ValidationError(f"Tax bracket {i + 1} {field} must be a valid number")

            # Validate income range
            if float(bracket['max_income']) <= float(bracket['min_income']):
                raise serializers.ValidationError(f"Tax bracket {i + 1} max income must be greater than min income")

        return brackets

    def validate_federal_tax_brackets(self, value):
        return self.validate_tax_brackets(value, "Federal")

    def validate_provincial_tax_brackets(self, value):
        return self.validate_tax_brackets(value, "Provincial")

    def validate_cpp(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("CPP rate must be between 0 and 100%")
        return value

    def validate_cpp_exemption(self, value):
        if value < 0:
            raise serializers.ValidationError("CPP basic exemption cannot be negative")
        return value

    def validate_cpp_cap(self, value):
        if value < 0:
            raise serializers.ValidationError("CPP maximum pensionable earnings cannot be negative")
        return value

    def validate(self, data):
        """Cross-field validation"""
        super().validate(data)

        # Ensure CPP cap is greater than CPP exemption
        cpp_exemption = data.get('cpp_exemption')
        cpp_cap = data.get('cpp_cap')

        if cpp_exemption and cpp_cap and cpp_cap <= cpp_exemption:
            raise serializers.ValidationError({
                'cpp_cap': 'CPP maximum pensionable earnings must be greater than the basic exemption'
            })

        return data

    def validate_ei_ee(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("EI employee rate must be between 0 and 100%")
        return value

    def validate_ei_er(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("EI employer rate must be between 0 and 100%")
        return value

    def validate_ei_cap(self, value):
        if value < 0:
            raise serializers.ValidationError("EI maximum insurable earnings cannot be negative")
        return value

    def validate_vacation_pay_rate(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Vacation pay rate must be between 0 and 100%")
        return value

    def validate_overtime_pay_rate(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Overtime pay rate multiplier must be at least 1.0 (e.g., 1.5 for time and a half)")
        if value > 10:
            raise serializers.ValidationError("Overtime pay rate multiplier seems unreasonably high (max 10)")
        return value


